"""Normalize stored amounts to the positive-amount convention.

R1 correctness fix. Going forward, ``Transaction.save`` stores income/expense
amounts as positive (sign carried by ``transaction_type``). This migration
repairs any rows written under the old convention where expenses were stored
negative, and any account balances stored as negative liabilities.

It is a no-op if data is already clean.
"""

from django.db import migrations


def normalize_transactions(apps, schema_editor):
    Transaction = apps.get_model("transactions", "Transaction")
    for tx in Transaction.objects.exclude(transaction_type="transfer").filter(amount__lt=0):
        tx.amount = -tx.amount
        tx.save(update_fields=["amount"])


def reverse_normalize_transactions(apps, schema_editor):
    # Best-effort reverse: re-negate expense rows. Income rows cannot be
    # safely distinguished post-migration, so leave them positive.
    Transaction = apps.get_model("transactions", "Transaction")
    for tx in Transaction.objects.filter(transaction_type="expense", amount__gt=0):
        tx.amount = -tx.amount
        tx.save(update_fields=["amount"])


def normalize_account_balances(apps, schema_editor):
    Account = apps.get_model("accounts", "Account")
    for acct in Account.objects.filter(balance__lt=0):
        acct.balance = -acct.balance
        acct.save(update_fields=["balance"])


def reverse_normalize_account_balances(apps, schema_editor):
    Account = apps.get_model("accounts", "Account")
    for acct in Account.objects.filter(
        account_type__in=("credit_card", "loan"), balance__gt=0
    ):
        acct.balance = -acct.balance
        acct.save(update_fields=["balance"])


class Migration(migrations.Migration):

    dependencies = [
        ("transactions", "0002_alter_transaction_options_transaction_is_reconciled_and_more"),
        ("accounts", "0002_alter_account_options_account_account_number_and_more"),
    ]

    operations = [
        migrations.RunPython(normalize_transactions, reverse_normalize_transactions),
        migrations.RunPython(normalize_account_balances, reverse_normalize_account_balances),
    ]
