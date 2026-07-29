from django import forms
from .models import Transaction

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ["account", "category", "amount", "date", "description"]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        self.fields["account"].queryset = self.user.accounts.all()
        self.fields["category"].queryset = self.user.categories.all()
