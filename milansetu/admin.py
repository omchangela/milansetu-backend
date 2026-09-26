from django.contrib import admin
from .models import UserInvite


@admin.register(UserInvite)
class UserInviteAdmin(admin.ModelAdmin):
	list_display = ("id", "requester", "target", "status", "created_at")
	list_filter = ("status",)
	search_fields = ("requester__email", "target__email")
