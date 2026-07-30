from django.contrib import admin
from django.contrib.auth.models import User
from apps.users.models import Profile

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at")
    search_fields = ("user__username",)

from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "is_active")
    list_filter = BaseUserAdmin.list_filter

admin.site.unregister(User)
admin.site.register(User, UserAdmin)
