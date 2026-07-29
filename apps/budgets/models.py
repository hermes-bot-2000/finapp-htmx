from django.db import models
from django.contrib.auth.models import User
from apps.categories.models import Category

class Budget(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="budgets")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="budgets")
    month = models.DateField()  # first day of month
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        unique_together = ("user", "category", "month")

    def __str__(self):
        return f"{self.category.name} - {self.month.strftime('%Y-%m')}: ${self.amount}"
