from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    """PRESENTER — safe user output (never exposes password)."""

    class Meta:
        model  = User
        fields = ['id', 'name', 'email', 'phone', 'address', 'role', 'created_at']
        read_only_fields = fields


class RegisterSerializer(serializers.Serializer):
    """PRESENTER — validates registration input."""

    name     = serializers.CharField(min_length=2, max_length=150)
    email    = serializers.EmailField()
    password = serializers.CharField(min_length=6, write_only=True)
    phone    = serializers.CharField(max_length=20, required=False, allow_blank=True)

    def validate_email(self, value):
        if User.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError('Email already registered.')
        return value.lower()


class LoginSerializer(serializers.Serializer):
    """PRESENTER — validates login input."""

    email    = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate_email(self, value):
        return value.lower()


class UpdateProfileSerializer(serializers.Serializer):
    """PRESENTER — validates profile update input."""

    name    = serializers.CharField(min_length=2, max_length=150, required=False)
    phone   = serializers.CharField(max_length=20, required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
