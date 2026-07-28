from django.contrib import admin
from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display  = ('id', 'user', 'type', 'date', 'time_slot', 'status', 'created_at')
    list_filter   = ('type', 'status', 'date')
    search_fields = ('user__email', 'doctor_name', 'notes')
    list_editable = ('status',)
    ordering      = ('-date', 'time_slot')

    fieldsets = (
        ('Appointment', {'fields': ('user', 'type', 'date', 'time_slot', 'doctor_name', 'notes')}),
        ('Status',      {'fields': ('status',)}),
        ('Timestamps',  {'fields': ('created_at',)}),
    )
    readonly_fields = ('created_at',)
