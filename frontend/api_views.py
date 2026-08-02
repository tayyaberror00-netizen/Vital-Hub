import logging

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from .models import NewsletterSubscriber, ContactMessage

logger = logging.getLogger('vitalhub')


class NewsletterSubscribeView(APIView):
    """POST /api/newsletter/subscribe/ — public. Real subscriber storage,
    not a fake front-end-only form."""
    permission_classes = [AllowAny]

    def post(self, request):
        email = (request.data.get('email') or '').strip().lower()
        if not email:
            return Response({'success': False, 'message': 'Email is required.'},
                             status=status.HTTP_400_BAD_REQUEST)
        try:
            validate_email(email)
        except ValidationError:
            return Response({'success': False, 'message': 'Please enter a valid email address.'},
                             status=status.HTTP_400_BAD_REQUEST)

        _, created = NewsletterSubscriber.objects.get_or_create(email=email)
        if not created:
            return Response({'success': True, 'message': "You're already subscribed!"})
        return Response({'success': True, 'message': 'Subscribed! Welcome to Vital Hub.'})


class ContactMessageView(APIView):
    """POST /api/contact/ — public. Stores the message AND emails it to
    the real Vital Hub inbox via Gmail SMTP — not a fake "message sent"
    confirmation with nothing actually happening behind it."""
    permission_classes = [AllowAny]

    def post(self, request):
        name    = (request.data.get('name') or '').strip()
        email   = (request.data.get('email') or '').strip().lower()
        subject = (request.data.get('subject') or '').strip()
        message = (request.data.get('message') or '').strip()

        if not name or not email or not message:
            return Response({'success': False, 'message': 'Name, email, and message are required.'},
                             status=status.HTTP_400_BAD_REQUEST)
        try:
            validate_email(email)
        except ValidationError:
            return Response({'success': False, 'message': 'Please enter a valid email address.'},
                             status=status.HTTP_400_BAD_REQUEST)

        record = ContactMessage.objects.create(
            name=name, email=email, subject=subject, message=message,
        )

        recipient = getattr(settings, 'CONTACT_RECIPIENT_EMAIL', '')
        sent = False
        if recipient:
            try:
                send_mail(
                    subject=f"[Vital Hub Contact] {subject or 'New message from ' + name}",
                    message=(
                        f"From: {name} <{email}>\n\n{message}\n\n"
                        f"— Sent via the Vital Hub contact form."
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[recipient],
                    fail_silently=False,
                )
                sent = True
            except Exception:
                # The message is already saved in the database either way —
                # an SMTP hiccup should never make the user think their
                # message vanished, and the admin can still see it.
                logger.exception('Contact form email dispatch failed')

        record.email_sent = sent
        record.save(update_fields=['email_sent'])

        return Response({
            'success': True,
            'message': "Thanks — your message has been sent. We'll get back to you soon."
                       if sent else "Thanks — your message has been received. (Email delivery is delayed, but we have it.)",
        })
