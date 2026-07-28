from django.urls import path
from django.views.generic import TemplateView

urlpatterns = [
    path('checkout.html',  TemplateView.as_view(template_name='orders/checkout.html')),
    path('thank-you.html', TemplateView.as_view(template_name='orders/thank-you.html')),
]
