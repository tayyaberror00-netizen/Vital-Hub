from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from .models import NewsletterSubscriber


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
