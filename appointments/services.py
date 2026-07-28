import logging
import datetime
from .models import Appointment
from .serializers import AppointmentSerializer

logger = logging.getLogger('vitalhub')


ALL_SLOTS = [
    '09:00', '09:30', '10:00', '10:30', '11:00', '11:30',
    '14:00', '14:30', '15:00', '15:30', '16:00', '16:30',
]


class AppointmentService:

    @staticmethod
    def available_slots(date_str: str, appt_type: str = 'general') -> list:
        try:
            date = datetime.date.fromisoformat(date_str)
        except ValueError:
            return []

        booked = set(
            Appointment.objects.filter(date=date, type=appt_type)
            .exclude(status='cancelled')
            .values_list('time_slot', flat=True)
        )
        return [s for s in ALL_SLOTS if s not in booked]

    @staticmethod
    def book(user, validated_data: dict) -> dict:
        date      = validated_data['date']
        time_slot = validated_data['time_slot']
        appt_type = validated_data['type']

        if time_slot not in ALL_SLOTS:
            raise ValueError(f'Invalid time slot. Must be one of: {", ".join(ALL_SLOTS)}')

        # Prevent double-booking the same slot
        conflict = Appointment.objects.filter(
            date=date, time_slot=time_slot, type=appt_type
        ).exclude(status='cancelled').exists()

        if conflict:
            raise ValueError('This slot is already booked. Please choose another.')

        appt = Appointment.objects.create(
            user=user,
            type=appt_type,
            date=date,
            time_slot=time_slot,
            notes=validated_data.get('notes', ''),
        )
        logger.info('Appointment booked: id=%s user=%s date=%s slot=%s', appt.pk, user.email, date, time_slot)
        return AppointmentSerializer(appt).data

    @staticmethod
    def my_appointments(user) -> list:
        appts = Appointment.objects.filter(user=user)
        return AppointmentSerializer(appts, many=True).data

    @staticmethod
    def cancel(user, appt_id: int) -> dict:
        try:
            appt = Appointment.objects.get(pk=appt_id, user=user)
        except Appointment.DoesNotExist:
            raise ValueError('Appointment not found.')

        if appt.status == 'cancelled':
            raise ValueError('Appointment is already cancelled.')

        appt.status = 'cancelled'
        appt.save()
        return AppointmentSerializer(appt).data
