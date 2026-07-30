from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal


class Account(models.Model):
    ACCOUNT_TYPES = (
        ("checking", "Checking"),
        ("savings", "Savings"),
        ("credit_card", "Credit Card"),
        ("cash", "Cash"),
        ("investment", "Investment"),
        ("loan", "Loan"),
        ("other", "Other"),
    )

    CURRENCY_CHOICES = (
        ("USD", "US Dollar (USD)"),
        ("EUR", "Euro (EUR)"),
        ("GBP", "British Pound (GBP)"),
        ("JPY", "Japanese Yen (JPY)"),
        ("CAD", "Canadian Dollar (CAD)"),
        ("AUD", "Australian Dollar (AUD)"),
        ("CHF", "Swiss Franc (CHF)"),
        ("CNY", "Chinese Yuan (CNY)"),
        ("INR", "Indian Rupee (INR)"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="accounts")
    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="USD")
    institution = models.CharField(max_length=100, blank=True, help_text="Bank or financial institution name")
    account_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Masked for security — only last 4 digits displayed",
    )
    routing_number = models.CharField(max_length=9, blank=True, help_text="ABA routing number (US accounts)")
    opened_date = models.DateField(null=True, blank=True, help_text="When the account was opened")
    interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.000"))],
        help_text="APY percentage (e.g. 2.500 for 2.5%)",
    )
    credit_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Credit limit for credit card accounts",
    )
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, help_text="Inactive accounts are hidden from lists")
    include_in_totals = models.BooleanField(default=True, help_text="Include in net worth and total calculations")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_active", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_account_type_display()})"

    @property
    def available_balance(self):
        """For credit cards: credit_limit - balance. For others: same as balance."""
        if self.account_type == "credit_card" and self.credit_limit is not None:
            return self.credit_limit - self.balance
        return self.balance

    @property
    def masked_account_number(self):
        """Return masked account number showing only last 4 digits."""
        if not self.account_number:
            return ""
        if len(self.account_number) <= 4:
            return self.account_number
        return "*" * (len(self.account_number) - 4) + self.account_number[-4:]
