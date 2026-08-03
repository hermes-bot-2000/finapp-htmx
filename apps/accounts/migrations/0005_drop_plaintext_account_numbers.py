"""F8: stop storing full account and routing numbers.

Adds ``account_number_last4``, back-fills it from the last four digits of any
existing ``account_number``, then drops both plaintext columns. The full
numbers are intentionally unrecoverable afterwards — that is the point of the
change — so the reverse migration restores the column shape but not the data.
"""
import re

from django.core.validators import RegexValidator
from django.db import migrations, models


def backfill_last4(apps, schema_editor):
    Account = apps.get_model("accounts", "Account")
    for account in Account.objects.exclude(account_number=""):
        digits = re.sub(r"\D", "", account.account_number or "")
        if digits:
            account.account_number_last4 = digits[-4:]
            account.save(update_fields=["account_number_last4"])


def noop_reverse(apps, schema_editor):
    """Full numbers were deliberately discarded; nothing to restore."""


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_account_opening_balance"),
    ]

    operations = [
        migrations.AddField(
            model_name="account",
            name="account_number_last4",
            field=models.CharField(
                blank=True,
                help_text="Last 4 digits only — full account numbers are never stored",
                max_length=4,
                validators=[RegexValidator(r"^\d{4}$", "Enter the last 4 digits.")],
            ),
        ),
        migrations.RunPython(backfill_last4, noop_reverse),
        migrations.RemoveField(model_name="account", name="account_number"),
        migrations.RemoveField(model_name="account", name="routing_number"),
    ]
