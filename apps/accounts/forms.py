from django import forms
from .models import Account


class AccountForm(forms.ModelForm):
    # Accept a longer paste so a full number can be truncated in clean() rather
    # than bounced back to the user still sitting in the form; the model field
    # itself stays max_length=4.
    account_number_last4 = forms.CharField(
        required=False,
        max_length=34,  # longest IBAN
        label="Account number (last 4)",
        help_text="Only the last 4 digits are saved.",
        widget=forms.TextInput(attrs={"inputmode": "numeric", "placeholder": "6789"}),
    )

    class Meta:
        model = Account
        fields = [
            "name", "account_type", "opening_balance", "currency",
            "institution", "account_number_last4",
            "opened_date", "interest_rate", "credit_limit",
            "notes", "is_active", "include_in_totals",
        ]
        widgets = {
            "opened_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "opening_balance": "Starting balance",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # currency has a model default; don't force it on the form.
        self.fields["currency"].required = False

    def clean_account_number_last4(self):
        """Never persist more than the last four digits (F8).

        A user pasting a full account number is a realistic accident; truncate
        it here so the full value never reaches the database, and reject
        anything that isn't digits.
        """
        value = (self.cleaned_data.get("account_number_last4") or "").strip()
        if not value:
            return ""
        if not value.isdigit():
            raise forms.ValidationError("Enter digits only.")
        return value[-4:]
