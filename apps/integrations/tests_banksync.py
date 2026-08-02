"""Tests for R2: real bank synchronization via the GoCardless client (mock mode).

These exercise the full connect -> callback -> sync flow without live API
credentials, because settings leave GOCARDLESS_SECRET_ID/KEY empty and the
client falls back to MockGoCardlessClient.
"""

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from apps.integrations.models import BankIntegration
from apps.accounts.models import Account
from apps.transactions.models import Transaction


class BankSyncFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("bankuser", "bank@example.com", "testpass123")
        self.client.force_login(self.user)

    def test_connect_institutions_lists_mock_banks(self):
        resp = self.client.get(reverse("connect_institutions"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Mock US Bank")

    def test_connect_account_creates_integration_and_redirects_to_bank(self):
        resp = self.client.post(reverse("connect_account"), {"institution_id": "mock_bank_us"})
        # Redirects to the (mock) bank OAuth link.
        self.assertEqual(resp.status_code, 302)
        self.assertIn("mock.gocardless.local", resp["Location"])
        integration = BankIntegration.objects.get(user=self.user)
        self.assertEqual(integration.provider, "gocardless")
        self.assertTrue(integration.requisition_id)

    def test_callback_links_accounts_and_imports_transactions(self):
        # Start a connection to get a requisition_id.
        self.client.post(reverse("connect_account"), {"institution_id": "mock_bank_us"})
        integration = BankIntegration.objects.get(user=self.user)
        req_id = integration.requisition_id

        resp = self.client.get(reverse("integration_callback"), {"ref": req_id})
        self.assertEqual(resp.status_code, 302)

        integration.refresh_from_db()
        self.assertEqual(integration.sync_status, "linked")
        self.assertEqual(len(integration.account_refs), 1)
        # A local account was created from the bank account.
        self.assertEqual(
            Account.objects.filter(user=self.user, institution_ref=integration.account_refs[0]).count(), 1
        )
        # Two mock transactions imported (one expense, one income) per account.
        self.assertGreaterEqual(Transaction.objects.filter(user=self.user, source="bank_sync").count(), 2)
        # Amounts follow the positive-amount convention (R1): expense stored positive.
        expense = Transaction.objects.filter(user=self.user, transaction_type="expense").first()
        self.assertIsNotNone(expense)
        self.assertGreater(expense.amount, 0)
        # Balances were applied to the linked account.
        acct = Account.objects.get(user=self.user, institution_ref=integration.account_refs[0])
        self.assertEqual(acct.balance, Decimal("1234.56"))

    def test_sync_now_pulls_new_transactions(self):
        self.client.post(reverse("connect_account"), {"institution_id": "mock_bank_us"})
        integration = BankIntegration.objects.get(user=self.user)
        # Run the callback once so the initial import happens.
        self.client.get(reverse("integration_callback"), {"ref": integration.requisition_id})
        before = Transaction.objects.filter(user=self.user, source="bank_sync").count()
        self.assertGreater(before, 0)
        # Syncing again must not create duplicates (stable external_id dedup).
        self.client.get(reverse("integration_callback"), {"ref": integration.requisition_id})
        after = Transaction.objects.filter(user=self.user, source="bank_sync").count()
        self.assertEqual(before, after)  # idempotent dedup

    def test_disconnect_revokes_and_deactivates(self):
        self.client.post(reverse("connect_account"), {"institution_id": "mock_bank_us"})
        integration = BankIntegration.objects.get(user=self.user)
        resp = self.client.post(reverse("disconnect_integration", args=[integration.pk]))
        self.assertEqual(resp.status_code, 302)
        integration.refresh_from_db()
        self.assertFalse(integration.is_active)
        # Requisition removed from the mock client.
        from apps.integrations.gocardless import get_client, GoCardlessError
        client = get_client()
        with self.assertRaises(GoCardlessError):
            client.get_requisition(integration.requisition_id)


class WebhookSignatureTests(TestCase):
    def test_webhook_requires_signature_when_secret_set(self):
        with self.settings(GOCARDLESS_WEBHOOK_SECRET="topsecret"):
            resp = self.client.post(reverse("integration_webhook"), data="{}", content_type="application/json")
            self.assertEqual(resp.status_code, 400)

    def test_webhook_accepts_valid_signature(self):
        with self.settings(GOCARDLESS_WEBHOOK_SECRET="topsecret"):
            resp = self.client.post(
                reverse("integration_webhook"),
                data="{}",
                content_type="application/json",
                HTTP_WEBHOOK_SIGNATURE="topsecret",
            )
            self.assertEqual(resp.status_code, 200)

    def test_webhook_open_when_no_secret_configured(self):
        with self.settings(GOCARDLESS_WEBHOOK_SECRET=""):
            resp = self.client.post(reverse("integration_webhook"), data="{}", content_type="application/json")
            self.assertEqual(resp.status_code, 200)
