from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class BaseIntegration(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="integrations")
    provider = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_synced = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def sync_transactions(self):
        raise NotImplementedError("Subclasses must implement sync_transactions")

    def fetch_balances(self):
        raise NotImplementedError("Subclasses must implement fetch_balances")


class BankIntegration(BaseIntegration):
    """A live open-banking connection (GoCardless / Nordigen).

    Only the GoCardless ``requisition_id`` is persisted. The access token is
    derived from the server secret on every call, so no user-bound secret is
    stored. ``account_refs`` keeps the mapping requisition -> remote account
    ids so syncs know which accounts to pull.
    """

    institution_id = models.CharField(max_length=100, blank=True)
    institution_name = models.CharField(max_length=100, blank=True)
    requisition_id = models.CharField(max_length=100, blank=True, unique=True)
    account_refs = models.JSONField(default=list, blank=True)
    sync_status = models.CharField(
        max_length=20,
        default="pending",
        choices=[
            ("pending", "Pending"),
            ("linked", "Linked"),
            ("error", "Error"),
        ],
    )
    last_error = models.TextField(blank=True)

    def sync_transactions(self):
        """Pull transactions for every linked account and return the count."""
        from apps.integrations.gocardless import get_client, parse_decimal, GoCardlessError
        from apps.transactions.models import Transaction
        from apps.categories.models import Category

        client = get_client()
        count = 0
        try:
            for account_id in self.account_refs:
                raw_txns = client.get_transactions(account_id)
                for raw in raw_txns:
                    amount_raw = raw.get("transactionAmount", {}).get("amount", "0")
                    amount = parse_decimal(amount_raw)
                    booking_date = raw.get("bookingDate") or raw.get("valueDate")
                    description = (
                        raw.get("remittanceInformationUnstructured")
                        or raw.get("remittanceInformationStructured")
                        or "Bank transaction"
                    )
                    # GoCardless returns signed amounts (negative = expense).
                    # Convert to our positive-amount convention (R1).
                    if amount < 0:
                        transaction_type = "expense"
                        amount = -amount
                    elif amount > 0:
                        transaction_type = "income"
                    else:
                        transaction_type = "transfer"

                    tx_id = raw.get("transactionId") or raw.get("internalTransactionId")
                    account = self._linked_account(account_id)
                    if account is None:
                        continue
                    defaults = {
                        "user": self.user,
                        "account": account,
                        "amount": amount,
                        "date": booking_date,
                        "description": description[:255],
                        "transaction_type": transaction_type,
                        "source": "bank_sync",
                    }
                    if tx_id:
                        obj, created = Transaction.objects.update_or_create(
                            user=self.user,
                            account=account,
                            external_id=tx_id,
                            defaults=defaults,
                        )
                    else:
                        obj, created = Transaction.objects.get_or_create(
                            user=self.user, account=account,
                            date=booking_date, description=description[:255],
                            defaults=defaults,
                        )
                    if created:
                        count += 1
            self.sync_status = "linked"
            self.last_error = ""
        except GoCardlessError as exc:
            self.sync_status = "error"
            self.last_error = str(exc)
        self.last_synced = timezone.now()
        self.save(update_fields=["sync_status", "last_error", "last_synced"])
        return count

    def fetch_balances(self) -> dict:
        """Pull current balances for linked accounts; returns {account_id: Decimal}."""
        from apps.integrations.gocardless import get_client, parse_decimal, GoCardlessError

        client = get_client()
        balances: dict = {}
        try:
            for account_id in self.account_refs:
                raw_balances = client.get_balances(account_id)
                if not raw_balances:
                    continue
                bal = raw_balances[0].get("balanceAmount", {}).get("amount", "0")
                balances[account_id] = parse_decimal(bal)
        except GoCardlessError as exc:
            self.sync_status = "error"
            self.last_error = str(exc)
            self.save(update_fields=["sync_status", "last_error"])
        return balances

    def _linked_account(self, account_id: str):
        from apps.accounts.models import Account

        # Account.institution_ref stores the remote account id set during linking.
        return Account.objects.filter(user=self.user, institution_ref=account_id).first()
