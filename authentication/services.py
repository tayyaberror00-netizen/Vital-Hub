import jwt
import uuid
import logging
from datetime import datetime, timezone, timedelta
from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from .models import User

logger = logging.getLogger('vitalhub')


class AuthService:
    """
    PRESENTER (Service) layer — all authentication business logic lives here.
    Views call this service; services never touch HTTP directly.
    """

    # ------------------------------------------------------------------ #
    #  Token factory                                                       #
    # ------------------------------------------------------------------ #

    TOKEN_LIFETIME = timedelta(hours=1)

    @staticmethod
    def generate_token(user: User) -> tuple[str, str]:
        """Return (encoded_jwt, jti). Token expires in 1 hour."""
        jti = uuid.uuid4().hex
        now = datetime.now(tz=timezone.utc)
        payload = {
            'id':  user.pk,
            'jti': jti,
            'exp': now + AuthService.TOKEN_LIFETIME,
            'iat': now,
        }
        token = jwt.encode(payload, settings.JWT_SECRET, algorithm='HS256')
        return token, jti

    # ------------------------------------------------------------------ #
    #  Business operations                                                 #
    # ------------------------------------------------------------------ #

    @staticmethod
    def register(validated_data: dict) -> tuple[User, str]:
        """Create a new user and return (user, token)."""
        user = User.objects.create_user(
            email    = validated_data['email'],
            name     = validated_data['name'],
            password = validated_data['password'],
            phone    = validated_data.get('phone', ''),
        )
        token, _ = AuthService.generate_token(user)
        logger.info('User registered: %s', user.email)
        return user, token

    @staticmethod
    def login(email: str, password: str) -> tuple[User, str]:
        """Verify credentials and return (user, token)."""
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            logger.warning('Login failed — unknown email: %s', email)
            raise AuthenticationFailed('Invalid email or password.')

        if not user.check_password(password):
            logger.warning('Login failed — wrong password for: %s', email)
            raise AuthenticationFailed('Invalid email or password.')

        if not user.is_active:
            raise AuthenticationFailed('Account is deactivated.')

        token, _ = AuthService.generate_token(user)
        logger.info('User logged in: %s', user.email)
        return user, token

    @staticmethod
    def logout(jti: str, exp: datetime) -> None:
        """Blacklist the current token so it cannot be reused."""
        from .models import TokenBlacklist
        TokenBlacklist.objects.get_or_create(
            jti=jti,
            defaults={'expires_at': exp},
        )
        logger.info('Token revoked: jti=%s', jti)

    @staticmethod
    def update_profile(user: User, data: dict) -> User:
        """Apply profile field updates and save."""
        for field in ('name', 'phone', 'address'):
            if field in data and data[field] is not None:
                setattr(user, field, data[field])
        user.save()
        return user
