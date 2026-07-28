from rest_framework import serializers
from .models import Product


class ProductSerializer(serializers.ModelSerializer):
    """Public read serializer — stock/is_active/created_at are read-only to prevent mass assignment."""

    class Meta:
        model  = Product
        fields = [
            'id', 'name', 'price', 'category', 'description',
            'features', 'img', 'images',
            'has_model', 'model_file', 'has_video', 'video_file',
            'stock', 'is_active', 'created_at',
        ]
        read_only_fields = ['stock', 'is_active', 'created_at']


class AdminProductSerializer(serializers.ModelSerializer):
    """Admin-only serializer — all fields writable (used by admin CRUD endpoints)."""

    class Meta:
        model  = Product
        fields = [
            'id', 'name', 'price', 'category', 'description',
            'features', 'img', 'images',
            'has_model', 'model_file', 'has_video', 'video_file',
            'stock', 'is_active', 'created_at',
        ]
        read_only_fields = ['created_at']


class ProductFilterSerializer(serializers.Serializer):
    """Validates query parameters for product listing."""

    category = serializers.ChoiceField(
        choices=[c[0] for c in Product.CATEGORY_CHOICES],
        required=False
    )
    search = serializers.CharField(max_length=100, required=False, allow_blank=True)
    sort   = serializers.ChoiceField(
        choices=['price_asc', 'price_desc', 'newest'],
        required=False,
        default='newest'
    )
    min_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, min_value=0)
    max_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, min_value=0)
    has_model = serializers.CharField(required=False, allow_blank=True)
    page  = serializers.IntegerField(min_value=1, default=1)
    limit = serializers.IntegerField(min_value=1, max_value=100, default=20)
