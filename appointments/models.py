from django.db import models
from django.conf import settings


class Appointment(models.Model):
    STATUS_CHOICES = [
        ('booked',    'Booked'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    TYPE_CHOICES = [
        ('general',      'General Consultation'),
        ('specialist',   'Specialist'),
        ('follow-up',    'Follow-up'),
        ('lab',          'Lab Test'),
        ('physiotherapy','Physiotherapy'),
    ]

    user         = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='appointments')
    type         = models.CharField(max_length=30, choices=TYPE_CHOICES, default='general')
    date         = models.DateField()
    time_slot    = models.CharField(max_length=20)   # e.g. "09:00"
    doctor_name  = models.CharField(max_length=200, blank=True)
    notes        = models.TextField(blank=True)
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='booked')
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', 'time_slot']
        unique_together = ('date', 'time_slot', 'type')

    def __str__(self):
        return f'{self.type} — {self.date} {self.time_slot} ({self.user.email})'
