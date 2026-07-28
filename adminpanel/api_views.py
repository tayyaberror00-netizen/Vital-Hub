import logging
import math
from django.db.models import Sum
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from products.models import Product
from products.serializers import AdminProductSerializer
from orders.models import Order
from orders.serializers import OrderSerializer
from appointments.models import Appointment
from appointments.serializers import AppointmentSerializer
from .permissions import AdminAPIView

logger = logging.getLogger('vitalhub')

PAGE_SIZE = 25


def _paginate(qs, request):
    """Return (page_qs, total, page, pages) for a queryset."""
    try:
        page = max(1, int(request.query_params.get('page', 1)))
    except (ValueError, TypeError):
        page = 1
    total = qs.count()
    pages = max(1, math.ceil(total / PAGE_SIZE))
    page  = min(page, pages)
    offset = (page - 1) * PAGE_SIZE
    return qs[offset:offset + PAGE_SIZE], total, page, pages


# ─── Dashboard ────────────────────────────────────────────────────────────────

class DashboardView(AdminAPIView, APIView):
    def get(self, request):
        today = timezone.now().date()
        data = {
            'total_products':       Product.objects.count(),
            'active_products':      Product.objects.filter(is_active=True).count(),
            'total_orders':         Order.objects.count(),
            'pending_orders':       Order.objects.filter(status='pending').count(),
            'total_revenue':        float(Order.objects.aggregate(t=Sum('total'))['t'] or 0),
            'todays_appointments':  Appointment.objects.filter(date=today).count(),
            'pending_appointments': Appointment.objects.filter(status='booked').count(),
            'recent_orders':        OrderSerializer(
                Order.objects.select_related('user').prefetch_related('items').order_by('-created_at')[:8],
                many=True,
            ).data,
        }
        return Response({'success': True, 'data': data})


# ─── Products ─────────────────────────────────────────────────────────────────

class AdminProductListView(AdminAPIView, APIView):
    def get(self, request):
        qs = Product.objects.all()
        q   = request.query_params.get('q')
        cat = request.query_params.get('category')
        if q:
            qs = qs.filter(name__icontains=q)
        if cat:
            qs = qs.filter(category=cat)
        qs, total, page, pages = _paginate(qs, request)
        return Response({
            'success': True,
            'total': total, 'page': page, 'pages': pages,
            'products': AdminProductSerializer(qs, many=True).data,
        })

    def post(self, request):
        serializer = AdminProductSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'errors': serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)
        product = serializer.save()
        logger.info('Admin %s created product id=%s name=%s', request.user.email, product.pk, product.name)
        return Response({'success': True, 'product': AdminProductSerializer(product).data},
                        status=status.HTTP_201_CREATED)


class AdminProductDetailView(AdminAPIView, APIView):
    def _get(self, pk):
        try:
            return Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return None

    def get(self, request, product_id):
        obj = self._get(product_id)
        if not obj:
            return Response({'success': False, 'message': 'Not found'}, status=404)
        return Response({'success': True, 'product': AdminProductSerializer(obj).data})

    def put(self, request, product_id):
        obj = self._get(product_id)
        if not obj:
            return Response({'success': False, 'message': 'Not found'}, status=404)
        serializer = AdminProductSerializer(obj, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({'success': False, 'errors': serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)
        product = serializer.save()
        logger.info('Admin %s updated product id=%s', request.user.email, product_id)
        return Response({'success': True, 'product': AdminProductSerializer(product).data})

    def delete(self, request, product_id):
        obj = self._get(product_id)
        if not obj:
            return Response({'success': False, 'message': 'Not found'}, status=404)
        obj.delete()
        logger.info('Admin %s deleted product id=%s', request.user.email, product_id)
        return Response({'success': True, 'message': 'Product deleted'})


# ─── Orders ───────────────────────────────────────────────────────────────────

class AdminOrderListView(AdminAPIView, APIView):
    def get(self, request):
        qs = Order.objects.select_related('user').prefetch_related('items').order_by('-created_at')
        s = request.query_params.get('status')
        if s:
            qs = qs.filter(status=s)
        qs, total, page, pages = _paginate(qs, request)
        orders = []
        for o in qs:
            d = OrderSerializer(o).data
            d['user_email'] = o.user.email
            d['user_name']  = o.user.name
            orders.append(d)
        return Response({'success': True, 'total': total, 'page': page, 'pages': pages, 'orders': orders})


class AdminOrderDetailView(AdminAPIView, APIView):
    STATUS_CHOICES = ['pending', 'confirmed', 'shipped', 'delivered', 'cancelled']

    def put(self, request, order_id):
        try:
            order = Order.objects.get(pk=order_id)
        except Order.DoesNotExist:
            return Response({'success': False, 'message': 'Not found'}, status=404)

        new_status = request.data.get('status')
        if new_status not in self.STATUS_CHOICES:
            return Response({'success': False, 'message': f'Invalid status. Choose from {self.STATUS_CHOICES}'},
                            status=status.HTTP_400_BAD_REQUEST)
        old_status = order.status
        order.status = new_status
        order.save()
        logger.info('Admin %s updated order id=%s: %s → %s', request.user.email, order_id, old_status, new_status)
        return Response({'success': True, 'order': OrderSerializer(order).data})


# ─── Appointments ─────────────────────────────────────────────────────────────

class AdminAppointmentListView(AdminAPIView, APIView):
    def get(self, request):
        qs = Appointment.objects.select_related('user').order_by('-date', 'time_slot')
        s = request.query_params.get('status')
        if s:
            qs = qs.filter(status=s)
        qs, total, page, pages = _paginate(qs, request)
        appts = []
        for a in qs:
            d = AppointmentSerializer(a).data
            d['user_email'] = a.user.email
            d['user_name']  = a.user.name
            appts.append(d)
        return Response({'success': True, 'total': total, 'page': page, 'pages': pages, 'appointments': appts})


class AdminAppointmentDetailView(AdminAPIView, APIView):
    STATUS_CHOICES = ['booked', 'confirmed', 'completed', 'cancelled']

    def put(self, request, appt_id):
        try:
            appt = Appointment.objects.get(pk=appt_id)
        except Appointment.DoesNotExist:
            return Response({'success': False, 'message': 'Not found'}, status=404)

        new_status = request.data.get('status')
        if new_status not in self.STATUS_CHOICES:
            return Response({'success': False, 'message': f'Invalid status. Choose from {self.STATUS_CHOICES}'},
                            status=status.HTTP_400_BAD_REQUEST)
        old_status = appt.status
        appt.status = new_status
        appt.save()
        logger.info('Admin %s updated appointment id=%s: %s → %s', request.user.email, appt_id, old_status, new_status)
        return Response({'success': True, 'appointment': AppointmentSerializer(appt).data})
