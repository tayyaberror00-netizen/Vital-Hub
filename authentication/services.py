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

    TOKEN_LIFETIME = timedelta(days=7)

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
    def google_login(id_token_str: str) -> tuple[User, str]:
        """Verify a Google ID token (from Google Identity Services on the
        frontend) and find-or-create the matching user. Returns (user, token)
        just like the regular email/password login, so the rest of the app
        never needs to know which auth method was used."""
        from google.oauth2 import id_token as google_id_token
        from google.auth.transport import requests as google_requests

        client_id = getattr(settings, 'GOOGLE_OAUTH_CLIENT_ID', '')
        if not client_id:
            raise AuthenticationFailed('Google sign-in is not configured on this server.')

        try:
            payload = google_id_token.verify_oauth2_token(
                id_token_str, google_requests.Request(), client_id,
            )
        except ValueError:
            logger.warning('Google OAuth: invalid or expired ID token presented')
            raise AuthenticationFailed('Google sign-in verification failed. Please try again.')

        if not payload.get('email_verified', False):
            raise AuthenticationFailed('Your Google account email is not verified.')

        sub   = payload['sub']
        email = payload['email'].lower()
        name  = payload.get('name') or email.split('@')[0]

        # 1. Already linked to this exact Google account — fastest path.
        user = User.objects.filter(google_sub=sub).first()

        # 2. First time signing in with Google, but an account with this
        #    email already exists (e.g. they originally signed up with a
        #    password) — link the two rather than creating a duplicate.
        if user is None:
            user = User.objects.filter(email=email).first()
            if user is not None:
                user.google_sub = sub
                user.save(update_fields=['google_sub'])
                logger.info('Linked existing account %s to Google', email)

        # 3. Genuinely new user — create a passwordless account.
        if user is None:
            user = User.objects.create_user(
                email=email, name=name, password=None,
                auth_provider='google', google_sub=sub,
            )
            logger.info('New user created via Google OAuth: %s', email)

        if not user.is_active:
            raise AuthenticationFailed('Account is deactivated.')

        token, _ = AuthService.generate_token(user)
        logger.info('User logged in via Google: %s', user.email)
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
