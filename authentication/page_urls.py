from django.urls import path
from django.views.generic import TemplateView

urlpatterns = [
    path('auth.html',      TemplateView.as_view(template_name='authentication/auth.html')),
    path('dashboard.html', TemplateView.as_view(template_name='authentication/dashboard.html')),
]
