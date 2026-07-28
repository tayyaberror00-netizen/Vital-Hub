from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from authentication.backends import JWTAuthentication
from .serializers import BookAppointmentSerializer, SlotsQuerySerializer
from .services import AppointmentService


def _auth_error():
    return Response({'success': False, 'message': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)


class AppointmentSlotsView(APIView):
    """GET /api/appointments/slots/?date=YYYY-MM-DD&type=general"""

    def get(self, request):
        serializer = SlotsQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        slots = AppointmentService.available_slots(
            str(serializer.validated_data['date']),
            serializer.validated_data.get('type', 'general'),
        )
        return Response({'success': True, 'slots': slots})


class AppointmentListView(APIView):
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        if not request.user or not request.user.is_authenticated:
            return _auth_error()
        appts = AppointmentService.my_appointments(request.user)
        return Response({'success': True, 'appointments': appts})

    def post(self, request):
        if not request.user or not request.user.is_authenticated:
            return _auth_error()

        serializer = BookAppointmentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        try:
            appt = AppointmentService.book(request.user, serializer.validated_data)
            return Response({'success': True, 'appointment': appt}, status=status.HTTP_201_CREATED)
        except ValueError as exc:
            return Response({'success': False, 'message': str(exc)}, status=status.HTTP_409_CONFLICT)


class AppointmentDetailView(APIView):
    authentication_classes = [JWTAuthentication]

    def delete(self, request, appt_id):
        if not request.user or not request.user.is_authenticated:
            return _auth_error()

        try:
            appt = AppointmentService.cancel(request.user, appt_id)
            return Response({'success': True, 'appointment': appt})
        except ValueError as exc:
            return Response({'success': False, 'message': str(exc)}, status=status.HTTP_404_NOT_FOUND)
