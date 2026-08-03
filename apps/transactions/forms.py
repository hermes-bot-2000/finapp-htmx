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


class TransactionFilterForm(forms.Form):
    """Validate the list-view query string (F4).

    Bad input is reported as a form error and the filter is skipped, rather
    than reaching the ORM and raising ``ValueError`` as a 500.
    """

    date_from = forms.DateField(required=False, label="From")
    date_to = forms.DateField(required=False, label="To")
    category = forms.ModelChoiceField(queryset=Category.objects.none(), required=False)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(
            Q(user=self.user) | Q(is_system=True)
        ).distinct()

    def filter(self, queryset):
        """Apply whichever filters validated; ignore the rest."""
        if not self.is_bound or not self.is_valid():
            return queryset
        data = self.cleaned_data
        if data.get("date_from"):
            queryset = queryset.filter(date__gte=data["date_from"])
        if data.get("date_to"):
            queryset = queryset.filter(date__lte=data["date_to"])
        if data.get("category"):
            queryset = queryset.filter(category=data["category"])
        return queryset
