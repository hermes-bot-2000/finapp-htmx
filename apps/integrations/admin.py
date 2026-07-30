from django.contrib import admin
from apps.integrations.models import BankIntegration

@admin.register(BankIntegration)
class BankIntegrationAdmin(admin.ModelAdmin):
    list_display = ("bank_name", "account_type", "provider", "is_active", "last_synced")
    list_filter = ("is_active", "provider")
    search_fields = ("bank_name", "provider")
