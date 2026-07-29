from django.db import models
from django.contrib.auth.models import User

class Category(models.Model):
    CATEGORY_TYPES = (
        ("income", "Income"),
        ("expense", "Expense"),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="categories")
    name = models.CharField(max_length=100)
    category_type = models.CharField(max_length=20, choices=CATEGORY_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.get_category_type_display()})"
