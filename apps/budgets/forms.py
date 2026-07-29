from django import forms
from .models import Budget
from apps.categories.models import Category

class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ["category", "month", "amount"]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(user=self.user, category_type="expense")
