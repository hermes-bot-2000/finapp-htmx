from django.contrib import admin
from apps.budgets.models import Budget

@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ("category", "month", "amount", "user")
    list_filter = ("month", "user")
    search_fields = ("category__name",)
