from django import forms
from .models import Account


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = [
            "name", "account_type", "balance", "currency",
            "institution", "account_number", "routing_number",
            "opened_date", "interest_rate", "credit_limit",
            "notes", "is_active", "include_in_totals",
        ]
        widgets = {
            "opened_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }
