from rest_framework.permissions import BasePermission

class IsMfaVerified(BasePermission):
    def has_permission(self, request, view):
        return request.session.get('mfa', False) is True
