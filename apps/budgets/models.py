from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from datetime import date, timedelta
from apps.categories.models import Category


class Budget(models.Model):
    BUDGET_TYPES = (
        ("monthly", "Monthly"),
        ("annual", "Annual"),
        ("rolling", "Rolling (custom period)"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="budgets")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="budgets")
    month = models.DateField(help_text="First day of the budget period")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    budget_type = models.CharField(max_length=10, choices=BUDGET_TYPES, default="monthly")
    period_start = models.DateField(null=True, blank=True, help_text="Actual start date of the budget period")
    period_end = models.DateField(null=True, blank=True, help_text="Actual end date of the budget period")
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, help_text="Inactive budgets are excluded from calculations")
    carried_over = models.BooleanField(default=False, help_text="Whether unused budget carries over to the next period")
    rollover_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Amount carried over from the previous period",
    )
    warning_threshold = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=80.00,
        validators=[MinValueValidator(Decimal("0.00")), MaxValueValidator(Decimal("100.00"))],
        help_text="Percentage of budget at which to show a warning (e.g. 80.00 for 80%)",
    )
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        ordering = ["-month", "category__name"]
        unique_together = ("user", "category", "month")

    def __str__(self):
        return f"{self.category.name} - {self.month.strftime('%Y-%m')}: ${self.amount}"

    def _get_period_end(self):
        """Calculate the end date of the budget period."""
        if self.period_end:
            return self.period_end
        start = self.period_start or self.month
        # Default: end of the month
        if start.month == 12:
            end = date(start.year + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(start.year, start.month + 1, 1) - timedelta(days=1)
        return end

    @property
    def total_budget(self):
        """Total budget including rollover from previous period."""
        return self.amount + self.rollover_amount

    @property
    def spent(self):
        """Calculate total spent in this budget period from transactions."""
        from apps.transactions.models import Transaction

        start = self.period_start or self.month
        end = self._get_period_end()
        spent = Transaction.objects.filter(
            user=self.user,
            category=self.category,
            date__gte=start,
            date__lte=end,
            transaction_type="expense",
        ).aggregate(models.Sum("amount"))["amount__sum"]
        return spent or Decimal("0.00")

    @property
    def remaining(self):
        """Remaining budget (total budget - spent)."""
        return self.total_budget - self.spent

    @property
    def spent_percent(self):
        """Percentage of budget spent."""
        if self.total_budget == 0:
            return Decimal("0.00")
        return (self.spent / self.total_budget) * 100

    @property
    def is_over_budget(self):
        """Check if spending has exceeded the budget."""
        return self.spent > self.total_budget

    @property
    def is_warning(self):
        """Check if spending has reached the warning threshold."""
        return self.spent_percent >= self.warning_threshold and not self.is_over_budget
