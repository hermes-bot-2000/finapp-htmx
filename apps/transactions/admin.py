from django.contrib import admin
from apps.transactions.models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("date", "account", "category", "amount", "payee", "transaction_type", "is_reconciled", "pending")
    list_filter = ("date", "account", "category", "transaction_type", "is_reconciled", "pending")
    search_fields = ("description", "payee", "memo", "reference_number", "tags", "account__name")
    date_hierarchy = "date"
    list_editable = ("is_reconciled", "pending")
    readonly_fields = ("created_at", "updated_at")
