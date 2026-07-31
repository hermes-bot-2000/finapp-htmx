from django import forms
from apps.accounts.models import Account


class StatementUploadForm(forms.Form):
    account = forms.ModelChoiceField(
        queryset=Account.objects.none(),
        help_text="Account this statement belongs to",
    )
    file = forms.FileField(help_text="CSV bank statement export")

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["account"].queryset = Account.objects.filter(user=user)
