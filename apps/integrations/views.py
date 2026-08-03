import hashlib
import hmac
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods

from apps.integrations.models import BankIntegration
from apps.integrations.gocardless import get_client, GoCardlessError


@login_required
def list_integrations(request):
    integrations = request.user.integrations.filter(is_active=True).select_related()
    return render(request, "integrations/list.html", {"integrations": integrations})


@login_required
def connect_institutions(request):
    """Step 1: list institutions (optionally filtered by country)."""
    country = request.GET.get("country")
    client = get_client()
    try:
        institutions = client.list_institutions(country)
    except GoCardlessError as exc:
        messages.error(request, f"Could not load banks: {exc}")
        institutions = []
    return render(
        request, "integrations/connect_institutions.html",
        {"institutions": institutions, "country": country or ""},
    )


@login_required
def connect_account(request):
    """Step 2: create a requisition and redirect the user to their bank's OAuth."""
    if request.method != "POST":
        return redirect("connect_institutions")
    institution_id = request.POST.get("institution_id")
    if not institution_id:
        return redirect("connect_institutions")
    client = get_client()
    redirect_url = request.build_absolute_uri(reverse("integration_callback"))
    try:
        agreement_id = client.create_agreement(institution_id)
        result = client.create_requisition(institution_id, redirect_url, agreement_id)
    except GoCardlessError as exc:
        messages.error(request, f"Could not start connection: {exc}")
        return redirect("connect_institutions")

    BankIntegration.objects.create(
        user=request.user,
        provider="gocardless",
        institution_id=institution_id,
        institution_name=_institution_name(client, institution_id),
        requisition_id=result["requisition_id"],
    )
    return redirect(result["link"])


def _institution_name(client, institution_id):
    try:
        for inst in client.list_institutions():
            if inst["id"] == institution_id:
                return inst["name"]
    except GoCardlessError:
        pass
    return institution_id


@login_required
def integration_callback(request):
    """Step 3: bank redirects back here with ?ref=requisition_id.

    Resolve the requisition to its linked accounts, create a local Account per
    remote account, and pull the first batch of transactions immediately.
    """
    ref = request.GET.get("ref") or request.GET.get("requisition_id")
    if not ref:
        messages.error(request, "Missing requisition reference.")
        return redirect("list_integrations")
    client = get_client()
    try:
        req = client.get_requisition(ref)
    except GoCardlessError as exc:
        messages.error(request, f"Connection failed: {exc}")
        return redirect("list_integrations")

    integration = BankIntegration.objects.filter(user=request.user, requisition_id=ref).first()
    if integration is None:
        integration = BankIntegration.objects.create(
            user=request.user, provider="gocardless", requisition_id=ref
        )
    integration.account_refs = req["account_ids"]
    integration.sync_status = "linked" if req["account_ids"] else "error"
    integration.last_synced = timezone.now()
    integration.save(update_fields=["account_refs", "sync_status", "last_synced"])

    _ensure_accounts(request.user, integration, client)
    if req["account_ids"]:
        messages.success(request, "Bank connected. Syncing transactions…")
        integration.sync_transactions()
        # The imported rows move the derived balance; reconcile back to the
        # balance the bank reports so the ledger and the bank agree.
        _apply_balances(integration, integration.fetch_balances())
    else:
        messages.warning(request, "Bank connected but no accounts were returned.")
    return redirect("list_integrations")


def _ensure_accounts(user, integration, client):
    """Create a local Account row per linked remote account (idempotent)."""
    from apps.accounts.models import Account

    for account_id in integration.account_refs:
        if Account.objects.filter(user=user, institution_ref=account_id).exists():
            continue
        balances = client.get_balances(account_id)
        balance = Decimal("0.00")
        currency = "USD"
        if balances:
            balance = Decimal(balances[0].get("balanceAmount", {}).get("amount", "0") or "0")
            currency = balances[0].get("balanceAmount", {}).get("currency", "USD")
        Account.objects.create(
            user=user,
            name=f"{integration.institution_name} Account",
            account_type="checking",
            opening_balance=balance,
            currency=currency,
            institution=integration.institution_name,
            institution_ref=account_id,
        )


@login_required
@require_POST
def sync_integration(request, pk):
    """Pulling from the bank is a side effect — POST only (F6)."""
    integration = get_object_or_404(BankIntegration, pk=pk, user=request.user)
    try:
        count = integration.sync_transactions()
        balances = integration.fetch_balances()
        _apply_balances(integration, balances)
        messages.success(request, f"Synced {count} new transaction(s).")
    except GoCardlessError as exc:
        messages.error(request, f"Sync failed: {exc}")
    return redirect("list_integrations")


def _apply_balances(integration, balances):
    from apps.accounts.models import Account

    for account_id, amount in balances.items():
        # The bank-reported balance is authoritative: reconcile the derived
        # ledger to it by absorbing the delta into opening_balance.
        for account in Account.objects.filter(
            user=integration.user, institution_ref=account_id
        ):
            account.set_current_balance(amount)


@login_required
@require_http_methods(["GET", "POST"])
def disconnect_integration(request, pk):
    integration = get_object_or_404(BankIntegration, pk=pk, user=request.user)
    if request.method == "POST":
        client = get_client()
        try:
            if integration.requisition_id:
                client.revoke_requisition(integration.requisition_id)
        except GoCardlessError as exc:
            messages.warning(request, f"Could not revoke at bank: {exc}")
        integration.is_active = False
        integration.save(update_fields=["is_active"])
        messages.success(request, "Bank connection removed.")
        return redirect("list_integrations")
    return render(request, "integrations/disconnect.html", {"integration": integration})


@csrf_exempt
@require_POST
def integration_webhook(request):
    """GoCardless pushes balance/transaction updates here.

    F7: this endpoint fails *closed*. With no ``GOCARDLESS_WEBHOOK_SECRET``
    configured there is no way to authenticate a caller, so the endpoint is
    unavailable rather than accepting anonymous writes. When a secret is set,
    the request body must carry a matching HMAC-SHA256 hex digest in the
    ``Webhook-Signature`` header, compared with ``hmac.compare_digest`` so the
    check is not timing-attackable.
    """
    secret = getattr(settings, "GOCARDLESS_WEBHOOK_SECRET", "")
    if not secret:
        return HttpResponse("webhook not configured", status=503)
    provided = request.headers.get("Webhook-Signature", "")
    expected = hmac.new(secret.encode(), request.body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(provided, expected):
        return HttpResponse("invalid signature", status=400)
    return HttpResponse("ok", status=200)
