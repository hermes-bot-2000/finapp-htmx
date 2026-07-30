from django import forms
from .models import Category


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = [
            "name", "category_type", "description", "parent",
            "icon", "color", "is_active", "sort_order",
        ]
        widgets = {
            "color": forms.TextInput(attrs={"type": "color"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        self.fields["parent"].queryset = Category.objects.filter(user=self.user, category_type=self.initial.get("category_type", "expense"))
