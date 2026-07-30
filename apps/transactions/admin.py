from django.contrib import admin
from apps.transactions.models import Transaction

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("date", "account", "category", "amount", "description")
    list_filter = ("date", "account", "category")
    search_fields = ("description", "account__name")
    date_hierarchy = "date"
