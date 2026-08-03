from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, RegexValidator
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
    opening_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Balance before any recorded transaction. The current balance is derived from the ledger.",
    )
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="USD")
    institution = models.CharField(max_length=100, blank=True, help_text="Bank or financial institution name")
    institution_ref = models.CharField(
        max_length=100, blank=True, help_text="Remote account id from the bank connection"
    )
    # F8: the app never needs the full account/routing number, so it does not
    # store them. Only the last four digits are kept — enough to tell two
    # accounts apart, useless to an attacker who reaches the database.
    account_number_last4 = models.CharField(
        max_length=4,
        blank=True,
        validators=[RegexValidator(r"^\d{4}$", "Enter the last 4 digits.")],
        help_text="Last 4 digits only — full account numbers are never stored",
    )
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

    LIABILITY_TYPES = ("credit_card", "loan")

    @property
    def is_liability(self):
        return self.account_type in self.LIABILITY_TYPES

    @property
    def computed_balance(self):
        """Current balance derived from the ledger — the single source of truth.

        Amounts are stored positive (see ``Transaction.save``); direction comes
        from ``transaction_type``. For asset accounts income adds and expense
        subtracts; for liabilities (credit card, loan) a charge *increases* the
        amount owed and a payment reduces it, so the signs invert. Transfers are
        excluded until they are modelled as paired legs (F13).
        """
        agg = self.transactions.aggregate(
            inflow=models.Sum("amount", filter=models.Q(transaction_type="income")),
            outflow=models.Sum("amount", filter=models.Q(transaction_type="expense")),
        )
        inflow = agg["inflow"] or Decimal("0.00")
        outflow = agg["outflow"] or Decimal("0.00")
        opening = self.opening_balance or Decimal("0.00")
        if self.is_liability:
            return opening + outflow - inflow
        return opening + inflow - outflow

    @property
    def balance(self):
        """Backwards-compatible alias for the derived current balance."""
        return self.computed_balance

    def set_current_balance(self, amount, save=True):
        """Reconcile to an authoritative balance (e.g. reported by the bank).

        Transactions are never rewritten; ``opening_balance`` absorbs the
        difference so that ``computed_balance == amount``.
        """
        amount = Decimal(amount)
        self.opening_balance = (self.opening_balance or Decimal("0.00")) + (
            amount - self.computed_balance
        )
        if save and self.pk:
            self.save(update_fields=["opening_balance"])
        return self.opening_balance

    @property
    def available_balance(self):
        """For credit cards: credit_limit - balance. For others: same as balance."""
        if self.account_type == "credit_card" and self.credit_limit is not None:
            return self.credit_limit - self.balance
        return self.balance

    @property
    def signed_balance(self):
        """Balance in net-worth terms.

        ``balance`` is always stored as a positive number. Liability accounts
        (credit cards, loans) are owed money, so their contribution to net
        worth is negative. Asset accounts contribute positively.
        """
        if self.is_liability:
            return -self.balance
        return self.balance

    @property
    def masked_account_number(self):
        """Display form of the stored last-4, e.g. ``••••6789``."""
        if not self.account_number_last4:
            return ""
        return f"••••{self.account_number_last4}"
