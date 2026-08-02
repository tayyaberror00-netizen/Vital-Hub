import jwt
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import User, TokenBlacklist


class JWTAuthentication(BaseAuthentication):
    """
    PRESENTER layer — custom JWT authentication backend.
    Reads 'Authorization: Bearer <token>' header and resolves the user.
    """

    def authenticate(self, request):
        auth = request.headers.get('Authorization', '')
        if not auth.startswith('Bearer '):
            return None

        token = auth.split(' ', 1)[1]
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token has expired. Please log in again.')
        except jwt.InvalidTokenError:
            raise AuthenticationFailed('Invalid token.')

        jti = payload.get('jti')
        if jti and TokenBlacklist.is_blacklisted(jti):
            raise AuthenticationFailed('Token has been revoked. Please log in again.')

        try:
            user = User.objects.get(pk=payload['id'])
        except User.DoesNotExist:
            raise AuthenticationFailed('Invalid token.')

        # Attach payload so views can access jti/exp without re-decoding
        request._jwt_payload = payload

        return (user, token)

    def authenticate_header(self, request):
        # Declaring this makes DRF return 401 (not 403) for missing/expired/
        # invalid tokens, which is the semantically correct status for "you
        # need to log in", vs 403 which means "you're logged in but not
        # allowed here".
        return 'Bearer'
