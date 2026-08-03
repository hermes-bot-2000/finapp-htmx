from django.contrib import admin
from apps.accounts.models import Account


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = (
        "name", "account_type", "opening_balance", "current_balance", "currency",
        "institution", "masked_account_number", "is_active", "include_in_totals",
        "created_at",
    )
    list_filter = ("account_type", "currency", "is_active", "created_at")
    search_fields = ("name", "institution")
    list_editable = ("is_active", "include_in_totals")

    @admin.display(description="Current balance")
    def current_balance(self, obj):
        return obj.computed_balance
