from django.contrib import admin
from apps.integrations.models import BankIntegration

@admin.register(BankIntegration)
class BankIntegrationAdmin(admin.ModelAdmin):
    list_display = ("institution_name", "provider", "sync_status", "is_active", "last_synced")
    list_filter = ("is_active", "provider", "sync_status")
    search_fields = ("institution_name", "provider", "requisition_id")
