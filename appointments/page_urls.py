from django.urls import path
from django.views.generic import TemplateView

urlpatterns = [
    path('appointment.html', TemplateView.as_view(template_name='appointments/appointment.html')),
]
