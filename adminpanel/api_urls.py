from django.urls import path
from .api_views import (
    DashboardView,
    AdminProductListView, AdminProductDetailView,
    AdminOrderListView, AdminOrderDetailView,
    AdminAppointmentListView, AdminAppointmentDetailView,
)

urlpatterns = [
    path('dashboard/',              DashboardView.as_view()),
    path('products/',               AdminProductListView.as_view()),
    path('products/<str:product_id>/', AdminProductDetailView.as_view()),
    path('orders/',                 AdminOrderListView.as_view()),
    path('orders/<int:order_id>/',  AdminOrderDetailView.as_view()),
    path('appointments/',           AdminAppointmentListView.as_view()),
    path('appointments/<int:appt_id>/', AdminAppointmentDetailView.as_view()),
]
