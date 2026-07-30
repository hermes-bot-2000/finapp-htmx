from django.contrib import admin
from apps.accounts.models import Account

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("name", "account_type", "balance", "created_at")
    list_filter = ("account_type", "created_at")
    search_fields = ("name",)
