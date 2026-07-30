from django.contrib import admin
from apps.categories.models import Category

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "category_type", "created_at")
    list_filter = ("category_type", "created_at")
    search_fields = ("name",)
