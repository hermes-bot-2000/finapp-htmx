from django.contrib import admin
from apps.accounts.models import Account


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("name", "account_type", "balance", "currency", "institution", "is_active", "include_in_totals", "created_at")
    list_filter = ("account_type", "currency", "is_active", "created_at")
    search_fields = ("name", "institution", "account_number")
    list_editable = ("is_active", "include_in_totals")
    readonly_fields = ("masked_account_number",)
