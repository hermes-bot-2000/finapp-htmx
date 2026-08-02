from django.db import models
from django.contrib.auth.models import User
from apps.accounts.models import Account
from apps.categories.models import Category


class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ("income", "Income"),
        ("expense", "Expense"),
        ("transfer", "Transfer"),
    )

    RECURRING_FREQUENCIES = (
        ("weekly", "Weekly"),
        ("biweekly", "Bi-weekly"),
        ("monthly", "Monthly"),
        ("quarterly", "Quarterly"),
        ("annually", "Annually"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="transactions")
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="transactions")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name="transactions")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()
    description = models.CharField(max_length=255, blank=True)
    payee = models.CharField(max_length=100, blank=True, help_text="Who the money went to or came from")
    memo = models.CharField(max_length=255, blank=True, help_text="Bank memo or additional details")
    notes = models.TextField(blank=True, help_text="Free-form notes")
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES, blank=True, help_text="Derived from category type but set explicitly for filtering")
    reference_number = models.CharField(max_length=100, blank=True, help_text="Check number, bank transaction ID, or other reference")
    is_recurring = models.BooleanField(default=False)
    recurring_frequency = models.CharField(max_length=10, choices=RECURRING_FREQUENCIES, blank=True)
    recurring_ends = models.DateField(null=True, blank=True, help_text="Date when recurring transaction ends")
    is_reconciled = models.BooleanField(default=False, help_text="Whether this transaction has been reconciled with a bank statement")
    reconciled_date = models.DateField(null=True, blank=True)
    pending = models.BooleanField(default=False, help_text="Whether this transaction is still pending (not yet settled)")
    tags = models.CharField(max_length=255, blank=True, help_text="Comma-separated tags for flexible categorization")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        indexes = [
            models.Index(fields=["user", "date"]),
            models.Index(fields=["user", "account", "date"]),
            models.Index(fields=["user", "is_reconciled"]),
            models.Index(fields=["user", "pending"]),
        ]

    def __str__(self):
        return f"{self.date} {self.category}: ${self.amount}"

    def save(self, *args, **kwargs):
        # Auto-derive transaction_type from category if not set
        if not self.transaction_type and self.category:
            self.transaction_type = self.category.category_type
        # Convention: income/expense amounts are stored as POSITIVE. The sign
        # of money is carried by ``transaction_type`` (income vs expense), which
        # matches how Quicken/Simplifi display and avoids aggregate-math traps.
        # Transfers keep the amount exactly as entered. This guard makes the
        # convention hold regardless of where the row came from (form, import,
        # management command).
        if (
            self.transaction_type in ("income", "expense")
            and self.amount is not None
        ):
            self.amount = abs(self.amount)
        super().save(*args, **kwargs)

    @property
    def is_transfer(self):
        """Check if this transaction is a transfer between accounts."""
        return self.transaction_type == "transfer"

    @property
    def tag_list(self):
        """Return tags as a list, split by comma."""
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(",") if tag.strip()]
