from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("email",)
    list_display = ("email", "user_type", "phone", "is_active", "is_staff", "date_joined")
    search_fields = ("email", "phone")
    list_filter = ("user_type", "is_staff", "is_active")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("phone", "user_type")}),
        ("Premium", {"fields": ("premium_since", "premium_expires_at", "profile_edit_count", "profile_edit_month")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "phone", "user_type", "password1", "password2"),
        }),
    )
    readonly_fields = ("date_joined",)
