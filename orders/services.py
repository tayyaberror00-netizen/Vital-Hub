import logging
from decimal import Decimal
from django.db import transaction
from django.db.models import F
from products.models import Product
from .models import Order, OrderItem
from .serializers import OrderSerializer

logger = logging.getLogger('vitalhub')


SHIPPING_THRESHOLD = Decimal('50000')  # free shipping above ₹500 (stored in paise)
SHIPPING_COST      = Decimal('9900')   # ₹99 flat


class OrderService:

    @staticmethod
    def place(user, validated_data: dict) -> dict:
        items_data       = validated_data['items']
        shipping_name    = validated_data['shipping_name']
        shipping_email   = user.email  # always use the authenticated user's email (prevent IDOR)
        shipping_address = validated_data['shipping_address']

        subtotal = sum(
            Decimal(str(item['price'])) * item['quantity']
            for item in items_data
        )
        shipping = Decimal('0') if subtotal >= SHIPPING_THRESHOLD else SHIPPING_COST
        total    = subtotal + shipping

        with transaction.atomic():
            for item in items_data:
                Product.objects.filter(
                    id=item['product_id'], stock__gte=item['quantity']
                ).update(stock=F('stock') - item['quantity'])

            order = Order.objects.create(
                user=user,
                shipping_name=shipping_name,
                shipping_email=shipping_email,
                shipping_address=shipping_address,
                subtotal=subtotal,
                shipping_cost=shipping,
                total=total,
            )

            OrderItem.objects.bulk_create([
                OrderItem(
                    order=order,
                    product_id=item['product_id'],
                    name=item['name'],
                    price=Decimal(str(item['price'])),
                    quantity=item['quantity'],
                    img=item.get('img', ''),
                )
                for item in items_data
            ])

        logger.info('Order placed: id=%s user=%s total=%s', order.pk, user.email, total)
        return OrderSerializer(order).data

    @staticmethod
    def my_orders(user) -> list:
        orders = Order.objects.filter(user=user).prefetch_related('items')
        return OrderSerializer(orders, many=True).data
