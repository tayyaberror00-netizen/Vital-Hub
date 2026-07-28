from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework import status
from authentication.backends import JWTAuthentication


class IsAdminRole(BasePermission):
    """DRF permission: user must be authenticated and have role='admin'."""

    message = 'Admin access required.'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and getattr(request.user, 'role', None) == 'admin'
        )


def admin_required(view_method):
    """Decorator for APIView methods — requires a valid JWT with role='admin'."""
    def wrapper(self, request, *args, **kwargs):
        auth = JWTAuthentication()
        try:
            result = auth.authenticate(request)
        except Exception:
            result = None

        if result is None:
            return Response({'success': False, 'message': 'Authentication required'},
                            status=status.HTTP_401_UNAUTHORIZED)

        user, _ = result
        if user.role != 'admin':
            return Response({'success': False, 'message': 'Admin access required'},
                            status=status.HTTP_403_FORBIDDEN)

        request.user = user
        return view_method(self, request, *args, **kwargs)
    return wrapper


class AdminAPIView:
    """Mixin that enforces admin-only access on every HTTP method."""
    authentication_classes = []
    permission_classes = []

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        auth = JWTAuthentication()
        try:
            result = auth.authenticate(request)
        except Exception:
            result = None

        if result is None:
            from rest_framework.exceptions import NotAuthenticated
            raise NotAuthenticated('Authentication required')

        user, _ = result
        if user.role != 'admin':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Admin access required')

        request.user = user
