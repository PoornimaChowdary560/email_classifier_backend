# accounts/permissions.py
from rest_framework import permissions

class IsAdmin(permissions.BasePermission):
    """
    Allows access only to admin-role users.
    """

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and getattr(user, "role", "") == "admin")
