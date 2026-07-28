from django.urls import path
from .views import AppointmentListView, AppointmentDetailView, AppointmentSlotsView

urlpatterns = [
    path('',              AppointmentListView.as_view()),
    path('slots/',        AppointmentSlotsView.as_view()),
    path('<int:appt_id>/', AppointmentDetailView.as_view()),
]
