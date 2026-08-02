from django import forms
from django.db.models import Q
from .models import Transaction
from apps.categories.models import Category


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = [
            "account", "category", "amount", "date", "description",
            "payee", "memo", "notes", "transaction_type",
            "reference_number", "is_recurring", "recurring_frequency",
            "recurring_ends", "is_reconciled", "reconciled_date",
            "pending", "tags",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "recurring_ends": forms.DateInput(attrs={"type": "date"}),
            "reconciled_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        self.fields["account"].queryset = self.user.accounts.filter(is_active=True)
        self.fields["category"].queryset = Category.objects.filter(
            Q(user=self.user) | Q(is_system=True), is_active=True
        ).distinct()
