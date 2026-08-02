"""GoCardless (Nordigen) Bank Account Data API client.

This implements the real open-banking flow documented at
https://gocardless.com/connect/ (formerly Nordigen). The same server-side
secret re-derives the access token on every call, so no per-user token is
stored on disk: only the short-lived ``requisition_id`` is persisted on the
BankIntegration row, and balances/transactions are pulled on demand.

Two implementations share one interface:

* ``GoCardlessClient``   - talks to the live API (needs GOCARDLESS_SECRET_ID/KEY).
* ``MockGoCardlessClient`` - in-memory stand-in used when the secret is unset,
  so the entire connect -> sync -> revoke flow is exercisable locally and in
  the test suite.

Use :func:`get_client` to obtain whichever is appropriate for the current
settings.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

import requests
from django.conf import settings
from django.utils import timezone as dj_timezone


class GoCardlessError(Exception):
    """Raised on any unrecoverable error talking to the bank API."""


class GoCardlessClient:
    """Live GoCardless Bank Account Data API client."""

    def __init__(self, secret_id: str, secret_key: str, base_url: str):
        if not secret_id or not secret_key:
            raise GoCardlessError("GOCARDLESS_SECRET_ID and GOCARDLESS_SECRET_KEY are required")
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.base_url = base_url.rstrip("/")
        self._token: str | None = None

    def _auth(self) -> str:
        if self._token:
            return self._token
        resp = requests.post(
            f"{self.base_url}/token/new",
            json={"secret_id": self.secret_id, "secret_key": self.secret_key},
            timeout=30,
        )
        if resp.status_code != 200:
            raise GoCardlessError(f"token request failed: {resp.status_code} {resp.text}")
        self._token = resp.json()["access"]
        return self._token

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._auth()}", "Accept": "application/json"}

    def _get(self, path: str) -> Any:
        resp = requests.get(f"{self.base_url}{path}", headers=self._headers(), timeout=30)
        if resp.status_code >= 400:
            raise GoCardlessError(f"GET {path} failed: {resp.status_code} {resp.text}")
        return resp.json()

    def _post(self, path: str, json: dict) -> Any:
        resp = requests.post(f"{self.base_url}{path}", json=json, headers=self._headers(), timeout=30)
        if resp.status_code >= 400:
            raise GoCardlessError(f"POST {path} failed: {resp.status_code} {resp.text}")
        return resp.json()

    def _delete(self, path: str) -> Any:
        resp = requests.delete(f"{self.base_url}{path}", headers=self._headers(), timeout=30)
        if resp.status_code >= 400:
            raise GoCardlessError(f"DELETE {path} failed: {resp.status_code} {resp.text}")
        return resp.json()

    def list_institutions(self, country: str | None = None) -> list[dict]:
        params = f"?country={country}" if country else ""
        data = self._get(f"/institutions/{params}")
        return [
            {"id": i["id"], "name": i["name"], "country": i.get("countries", [None])[0]}
            for i in data
        ]

    def create_agreement(self, institution_id: str, max_days: int = 90) -> str:
        data = self._post(
            "/agreements/enduser/",
            {"institution_id": institution_id, "max_historical_days": max_days, "access_valid_for_days": 90},
        )
        return data["id"]

    def create_requisition(self, institution_id: str, redirect_url: str, agreement_id: str) -> dict:
        data = self._post(
            "/requisitions/",
            {"redirect": redirect_url, "institution_id": institution_id, "agreement": agreement_id},
        )
        return {"requisition_id": data["id"], "link": data["link"]}

    def get_requisition(self, requisition_id: str) -> dict:
        data = self._get(f"/requisitions/{requisition_id}/")
        return {
            "requisition_id": data["id"],
            "status": data.get("status"),
            "account_ids": data.get("accounts", []),
        }

    def get_balances(self, account_id: str) -> list[dict]:
        data = self._get(f"/accounts/{account_id}/balances/")
        return [b for b in data.get("balances", [])]

    def get_transactions(self, account_id: str) -> list[dict]:
        data = self._get(f"/accounts/{account_id}/transactions/")
        out = []
        for group in ("booked", "pending"):
            for tx in data.get("transactions", {}).get(group, []):
                tx = dict(tx)
                tx["_status"] = group
                out.append(tx)
        return out

    def revoke_requisition(self, requisition_id: str) -> None:
        self._delete(f"/requisitions/{requisition_id}/")


class MockGoCardlessClient:
    """In-memory client mirroring the live API for local dev and tests."""

    def __init__(self):
        self._institutions = [
            {"id": "mock_bank_us", "name": "Mock US Bank", "country": "US"},
            {"id": "mock_bank_eu", "name": "Mock EU Bank", "country": "DE"},
        ]
        self._requisitions: dict[str, dict] = {}
        self._counter = 0

    def list_institutions(self, country: str | None = None) -> list[dict]:
        insts = self._institutions
        if country:
            insts = [i for i in insts if i["country"] == country]
        return [{"id": i["id"], "name": i["name"], "country": i["country"]} for i in insts]

    def create_agreement(self, institution_id: str, max_days: int = 90) -> str:
        self._counter += 1
        return f"agr_mock_{self._counter}"

    def create_requisition(self, institution_id: str, redirect_url: str, agreement_id: str) -> dict:
        self._counter += 1
        req_id = f"req_mock_{self._counter}"
        self._requisitions[req_id] = {
            "requisition_id": req_id,
            "status": "CR",  # created
            "account_ids": [f"acc_mock_{self._counter}"],
        }
        return {
            "requisition_id": req_id,
            "link": f"https://mock.gocardless.local/link/{req_id}?redirect={redirect_url}",
        }

    def get_requisition(self, requisition_id: str) -> dict:
        if requisition_id not in self._requisitions:
            raise GoCardlessError(f"unknown requisition {requisition_id}")
        return dict(self._requisitions[requisition_id])

    def get_balances(self, account_id: str) -> list[dict]:
        return [
            {"balanceAmount": {"amount": "1234.56", "currency": "USD"}, "balanceType": "closingBooked"},
        ]

    def get_transactions(self, account_id: str) -> list[dict]:
        return [
            {
                "_status": "booked",
                "transactionId": f"{account_id}-t1",
                "bookingDate": "2026-07-20",
                "valueDate": "2026-07-20",
                "transactionAmount": {"amount": "-52.30", "currency": "USD"},
                "remittanceInformationUnstructured": "WHOLE FOODS MARKET",
            },
            {
                "_status": "booked",
                "transactionId": f"{account_id}-t2",
                "bookingDate": "2026-07-22",
                "valueDate": "2026-07-22",
                "transactionAmount": {"amount": "2500.00", "currency": "USD"},
                "remittanceInformationUnstructured": "PAYROLL DIRECT DEPOSIT",
            },
        ]

    def revoke_requisition(self, requisition_id: str) -> None:
        self._requisitions.pop(requisition_id, None)


def get_client():
    """Return a live client if credentials are configured, else the mock.

    The mock is a process-wide singleton so requisitions created during a
    connect flow survive until the callback reads them back in the same run.
    """
    if settings.GOCARDLESS_SECRET_ID and settings.GOCARDLESS_SECRET_KEY:
        return GoCardlessClient(
            settings.GOCARDLESS_SECRET_ID,
            settings.GOCARDLESS_SECRET_KEY,
            settings.GOCARDLESS_BASE_URL,
        )
    global _mock_client
    if _mock_client is None:
        _mock_client = MockGoCardlessClient()
    return _mock_client


_mock_client = None


def parse_decimal(raw: Any) -> Decimal:
    try:
        return Decimal(str(raw))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0.00")
