from rest_framework import serializers
from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model  = OrderItem
        fields = ('product_id', 'name', 'price', 'quantity', 'img')


class OrderItemInputSerializer(serializers.Serializer):
    product_id = serializers.CharField()
    name       = serializers.CharField()
    price      = serializers.DecimalField(max_digits=10, decimal_places=2)
    quantity   = serializers.IntegerField(min_value=1)
    img        = serializers.CharField(required=False, allow_blank=True, default='')


class PlaceOrderSerializer(serializers.Serializer):
    shipping_name    = serializers.CharField(max_length=200)
    shipping_email   = serializers.EmailField()
    shipping_address = serializers.CharField()
    items            = OrderItemInputSerializer(many=True, min_length=1)


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model  = Order
        fields = (
            'id', 'status',
            'shipping_name', 'shipping_email', 'shipping_address',
            'subtotal', 'shipping_cost', 'total',
            'items', 'created_at',
        )
