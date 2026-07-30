from django.db import models
from django.contrib.auth.models import User


class Category(models.Model):
    CATEGORY_TYPES = (
        ("income", "Income"),
        ("expense", "Expense"),
        ("transfer", "Transfer"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="categories")
    name = models.CharField(max_length=100)
    category_type = models.CharField(max_length=20, choices=CATEGORY_TYPES)
    description = models.TextField(blank=True, help_text="Description of what this category covers")
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
        help_text="Parent category for hierarchical organization",
    )
    icon = models.CharField(max_length=50, blank=True, help_text="Icon name or class for UI display")
    color = models.CharField(max_length=7, blank=True, help_text="Hex color code for UI display (e.g. #FF5733)")
    is_active = models.BooleanField(default=True, help_text="Inactive categories are hidden from lists")
    is_system = models.BooleanField(default=False, help_text="System categories cannot be deleted")
    sort_order = models.PositiveIntegerField(default=0, help_text="Order in which categories are displayed")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category_type", "sort_order", "name"]
        unique_together = ("user", "name")

    def __str__(self):
        return f"{self.name} ({self.get_category_type_display()})"

    @property
    def full_name(self):
        """Return the full hierarchical name, e.g. 'Food > Groceries'."""
        if self.parent:
            return f"{self.parent.full_name} > {self.name}"
        return self.name

    @property
    def is_parent(self):
        """Check if this category has children."""
        return self.children.exists()

    @property
    def depth(self):
        """Return the depth in the hierarchy (0 = top-level)."""
        depth = 0
        parent = self.parent
        while parent:
            depth += 1
            parent = parent.parent
        return depth
