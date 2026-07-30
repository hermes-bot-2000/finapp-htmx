from django import forms
from .models import Budget
from apps.categories.models import Category


class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = [
            "category", "month", "amount", "budget_type",
            "period_start", "period_end", "notes",
            "is_active", "carried_over", "rollover_amount",
            "warning_threshold",
        ]
        widgets = {
            "month": forms.DateInput(attrs={"type": "date"}),
            "period_start": forms.DateInput(attrs={"type": "date"}),
            "period_end": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(user=self.user, category_type="expense")
