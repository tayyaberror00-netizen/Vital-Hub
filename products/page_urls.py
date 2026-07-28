from django.urls import path
from django.views.generic import TemplateView

urlpatterns = [
    path('store.html',          TemplateView.as_view(template_name='products/store.html')),
    path('product-detail.html', TemplateView.as_view(template_name='products/product-detail.html')),
]
