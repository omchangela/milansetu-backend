from rest_framework.permissions import BasePermission


class IsEmployeeOrAdmin(BasePermission):
    """Staff users (is_staff) can browse all profiles."""

    def has_permission(self, request, view):
        user = request.user
        return user.is_authenticated and user.is_staff


class IsAdminRole(BasePermission):
    """Superusers only — destructive admin operations."""

    def has_permission(self, request, view):
        user = request.user
        return user.is_authenticated and user.is_superuser
