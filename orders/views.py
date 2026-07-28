from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from authentication.backends import JWTAuthentication
from .serializers import PlaceOrderSerializer
from .services import OrderService


class OrderListView(APIView):
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        if not request.user or not request.user.is_authenticated:
            return Response({'success': False, 'message': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        orders = OrderService.my_orders(request.user)
        return Response({'success': True, 'orders': orders})

    def post(self, request):
        if not request.user or not request.user.is_authenticated:
            return Response({'success': False, 'message': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = PlaceOrderSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        try:
            order = OrderService.place(request.user, serializer.validated_data)
            return Response({'success': True, 'order': order}, status=status.HTTP_201_CREATED)
        except Exception as exc:
            return Response({'success': False, 'message': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
