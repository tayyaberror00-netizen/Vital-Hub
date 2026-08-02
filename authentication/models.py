from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """Custom manager — email is the unique identifier, not username."""

    def create_user(self, email, name, password=None, **extra):
        if not email:
            raise ValueError('Email is required')
        user = self.model(email=self.normalize_email(email), name=name, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, password=None, **extra):
        extra.setdefault('role', 'admin')
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        return self.create_user(email, name, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    """
    MODEL layer — represents a registered Vital Hub user.
    Uses email as the login credential instead of username.
    """

    ROLE_CHOICES = [('user', 'User'), ('admin', 'Admin')]

    email   = models.EmailField(unique=True)
    name    = models.CharField(max_length=150)
    phone   = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    role    = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')

    AUTH_PROVIDER_CHOICES = [('email', 'Email/Password'), ('google', 'Google')]
    auth_provider = models.CharField(max_length=10, choices=AUTH_PROVIDER_CHOICES, default='email')
    google_sub    = models.CharField(max_length=64, unique=True, null=True, blank=True,
                                      help_text="Google's stable unique subject ID — safer than matching on email alone.")

    is_active   = models.BooleanField(default=True)
    is_staff    = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['name']

    class Meta:
        db_table = 'users'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} <{self.email}>'


class TokenBlacklist(models.Model):
    """Stores revoked JWT IDs so logged-out tokens cannot be reused."""

    jti        = models.CharField(max_length=64, unique=True, db_index=True)
    revoked_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = 'token_blacklist'

    @classmethod
    def is_blacklisted(cls, jti: str) -> bool:
        return cls.objects.filter(jti=jti).exists()

    @classmethod
    def purge_expired(cls):
        cls.objects.filter(expires_at__lt=timezone.now()).delete()
