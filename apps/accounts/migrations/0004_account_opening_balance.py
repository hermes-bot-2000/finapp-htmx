"""F1: make Account.balance a derived value.

The stored ``balance`` column becomes ``opening_balance`` (a plain rename, so no
data is lost), then existing rows are back-solved: the number the user was
looking at yesterday was the *current* balance, so the opening balance must be
that value minus whatever the already-recorded transactions contribute. This
keeps every account's displayed balance identical across the upgrade while
making it a function of the ledger from here on.
"""
from decimal import Decimal

from django.db import migrations, models

LIABILITY_TYPES = ("credit_card", "loan")


def _ledger_delta(Transaction, account):
    inflow = Decimal("0.00")
    outflow = Decimal("0.00")
    for tx in Transaction.objects.filter(account_id=account.pk):
        if tx.transaction_type == "income":
            inflow += abs(tx.amount or Decimal("0.00"))
        elif tx.transaction_type == "expense":
            outflow += abs(tx.amount or Decimal("0.00"))
    if account.account_type in LIABILITY_TYPES:
        return outflow - inflow
    return inflow - outflow


def backsolve_opening_balance(apps, schema_editor):
    Account = apps.get_model("accounts", "Account")
    Transaction = apps.get_model("transactions", "Transaction")
    for account in Account.objects.all():
        delta = _ledger_delta(Transaction, account)
        if delta:
            account.opening_balance = (account.opening_balance or Decimal("0.00")) - delta
            account.save(update_fields=["opening_balance"])


def restore_stored_balance(apps, schema_editor):
    Account = apps.get_model("accounts", "Account")
    Transaction = apps.get_model("transactions", "Transaction")
    for account in Account.objects.all():
        delta = _ledger_delta(Transaction, account)
        if delta:
            account.opening_balance = (account.opening_balance or Decimal("0.00")) + delta
            account.save(update_fields=["opening_balance"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_account_institution_ref"),
        ("transactions", "0003_normalize_amount_signs"),
    ]

    operations = [
        migrations.RenameField(
            model_name="account",
            old_name="balance",
            new_name="opening_balance",
        ),
        migrations.AlterField(
            model_name="account",
            name="opening_balance",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text=(
                    "Balance before any recorded transaction. The current balance "
                    "is derived from the ledger."
                ),
                max_digits=12,
            ),
        ),
        migrations.RunPython(backsolve_opening_balance, restore_stored_balance),
    ]
