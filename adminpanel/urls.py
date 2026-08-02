from django.urls import path
from . import page_views

urlpatterns = [
    path('',               page_views.dashboard),
    path('products/',      page_views.products),
    path('orders/',        page_views.orders),
    path('appointments/',  page_views.appointments),
    path('users/',         page_views.users),
]
