from rest_framework import serializers
from .models import Appointment


class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Appointment
        fields = ('id', 'type', 'date', 'time_slot', 'doctor_name', 'notes', 'status', 'created_at')


class BookAppointmentSerializer(serializers.Serializer):
    TYPE_CHOICES = [c[0] for c in Appointment.TYPE_CHOICES]

    type      = serializers.ChoiceField(choices=TYPE_CHOICES)
    date      = serializers.DateField()
    time_slot = serializers.CharField(max_length=20)
    notes     = serializers.CharField(required=False, allow_blank=True, default='')


class SlotsQuerySerializer(serializers.Serializer):
    date = serializers.DateField()
    type = serializers.CharField(required=False, default='general')
