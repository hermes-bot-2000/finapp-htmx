from django.contrib import admin
from apps.budgets.models import Budget


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ("category", "month", "amount", "budget_type", "is_active", "spent", "remaining", "user")
    list_filter = ("month", "budget_type", "is_active", "user")
    search_fields = ("category__name", "notes")
    list_editable = ("is_active",)
    readonly_fields = ("created_at", "updated_at")
