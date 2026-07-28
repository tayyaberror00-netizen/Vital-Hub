import logging
from datetime import datetime, timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import AnonRateThrottle

from .serializers import RegisterSerializer, LoginSerializer, UpdateProfileSerializer, UserSerializer
from .services import AuthService

logger = logging.getLogger('vitalhub')


class LoginRateThrottle(AnonRateThrottle):
    scope = 'login'


class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            first_error = next(iter(serializer.errors.values()))[0]
            return Response({'success': False, 'message': str(first_error)},
                            status=status.HTTP_400_BAD_REQUEST)

        user, token = AuthService.register(serializer.validated_data)
        return Response({
            'success': True,
            'token':   token,
            'user':    UserSerializer(user).data,
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'message': 'Invalid credentials.'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            user, token = AuthService.login(
                serializer.validated_data['email'],
                serializer.validated_data['password'],
            )
        except Exception:
            # Never leak internal error details to the client
            return Response({'success': False, 'message': 'Invalid email or password.'},
                            status=status.HTTP_401_UNAUTHORIZED)

        # Set session flag so admin page views can do server-side guard
        if user.role == 'admin':
            request.session['vh_is_admin'] = True
            request.session['vh_user_id']  = user.pk
        else:
            request.session.flush()

        return Response({'success': True, 'token': token, 'user': UserSerializer(user).data})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        payload = getattr(request, '_jwt_payload', None)
        if payload and payload.get('jti'):
            exp = datetime.fromtimestamp(payload['exp'], tz=timezone.utc)
            AuthService.logout(payload['jti'], exp)
        request.session.flush()
        return Response({'success': True, 'message': 'Logged out successfully.'})


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({'success': True, 'user': UserSerializer(request.user).data})

    def put(self, request):
        serializer = UpdateProfileSerializer(data=request.data)
        if not serializer.is_valid():
            first_error = next(iter(serializer.errors.values()))[0]
            return Response({'success': False, 'message': str(first_error)},
                            status=status.HTTP_400_BAD_REQUEST)

        user = AuthService.update_profile(request.user, serializer.validated_data)
        return Response({'success': True, 'user': UserSerializer(user).data})
