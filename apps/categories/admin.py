from django.contrib import admin
from apps.categories.models import Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "category_type", "parent", "is_active", "is_system", "sort_order", "created_at")
    list_filter = ("category_type", "is_active", "is_system", "created_at")
    search_fields = ("name", "description")
    list_editable = ("is_active", "sort_order")
    readonly_fields = ("created_at", "updated_at")
