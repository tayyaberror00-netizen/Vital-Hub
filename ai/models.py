from django.conf import settings
from django.db import models


class AIUsageLog(models.Model):
    """One row per AI feature use — powers both quota enforcement (count rows
    in the relevant window) and the admin activity dashboard (list rows)."""

    ACTION_CHOICES = [
        ('nutrition_plan', 'Nutrition Plan Generated'),
        ('xray_scan',       'X-Ray Scan'),
        ('report_scan',     'Medical Report Scan'),
    ]

    user        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                     related_name='ai_usage_logs')
    action_type = models.CharField(max_length=30, choices=ACTION_CHOICES)
    # Free-form context for the admin activity view — e.g. the uploaded
    # filename for scans, or a short summary for a generated plan.
    detail      = models.CharField(max_length=255, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ai_usage_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'action_type', 'created_at']),
        ]

    def __str__(self):
        return f'{self.user.email} — {self.action_type} @ {self.created_at:%Y-%m-%d %H:%M}'
