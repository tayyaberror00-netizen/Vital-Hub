from django.urls import path
from django.views.generic import TemplateView
from .page_views import AuthPageView

urlpatterns = [
    path('auth.html',      AuthPageView.as_view()),
    path('dashboard.html', TemplateView.as_view(template_name='authentication/dashboard.html')),
]
