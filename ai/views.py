import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

logger = logging.getLogger('vitalhub')

def _first_error(errors):
    """Flatten DRF serializer.errors into one human-readable message."""
    for field, msgs in errors.items():
        msg = msgs[0] if isinstance(msgs, list) else msgs
        return f"{field}: {msg}"
    return "Invalid request."


from .serializers import (
    NutritionInputSerializer, ConsultationChatSerializer,
    NutritionPlanSerializer, GroceryListSerializer,
)
from .services import (
    NutritionService, XrayService, ConsultationService,
    NutritionPlanService, ReportAnalyzerService,
)


class NutritionView(APIView):
    permission_classes = [AllowAny]
    parser_classes     = [JSONParser, FormParser]

    def post(self, request):
        serializer = NutritionInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'success': False, 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            result = NutritionService.calculate(**serializer.validated_data)
            return Response({'success': True, **result})
        except Exception as e:
            return Response(
                {'success': False, 'message': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class XrayView(APIView):
    permission_classes = [AllowAny]
    parser_classes     = [MultiPartParser, FormParser]

    def post(self, request):
        image = request.FILES.get('image')
        if not image:
            return Response(
                {'success': False, 'message': 'No image file provided.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            result = XrayService.analyze(image)
            return Response({'success': True, **result})
        except ValueError as e:
            return Response(
                {'success': False, 'message': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {'success': False, 'message': 'Analysis failed. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ConsultationChatView(APIView):
    permission_classes = [AllowAny]
    parser_classes     = [JSONParser]

    def post(self, request):
        serializer = ConsultationChatSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'errors': serializer.errors, 'message': _first_error(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)
        try:
            reply = ConsultationService.chat(
                serializer.validated_data['message'],
                serializer.validated_data.get('history', []),
            )
            return Response({'success': True, 'response': reply})
        except ValueError as e:
            return Response({'success': False, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("AI endpoint error")
            return Response(
                {'success': False, 'message': 'AI service unavailable. Please try again.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


class NutritionPlanView(APIView):
    permission_classes = [AllowAny]
    parser_classes     = [JSONParser]

    def post(self, request):
        serializer = NutritionPlanSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'errors': serializer.errors, 'message': _first_error(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)
        try:
            plan = NutritionPlanService.generate_week_plan(serializer.validated_data)
            return Response({'success': True, **plan})
        except ValueError as e:
            return Response({'success': False, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("AI endpoint error")
            return Response(
                {'success': False, 'message': 'AI service unavailable. Please try again.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


class GroceryListView(APIView):
    permission_classes = [AllowAny]
    parser_classes     = [JSONParser]

    def post(self, request):
        serializer = GroceryListSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'errors': serializer.errors, 'message': _first_error(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)
        try:
            groceries = NutritionPlanService.generate_grocery_list(serializer.validated_data['week_plan'])
            return Response({'success': True, **groceries})
        except ValueError as e:
            return Response({'success': False, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("AI endpoint error")
            return Response(
                {'success': False, 'message': 'AI service unavailable. Please try again.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


class ReportAnalyzerView(APIView):
    permission_classes = [AllowAny]
    parser_classes     = [MultiPartParser, FormParser]

    def post(self, request):
        report_file = request.FILES.get('report')
        if not report_file:
            return Response({'success': False, 'message': 'No report file provided.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            result = ReportAnalyzerService.analyze(report_file)
            return Response({'success': True, **result})
        except ValueError as e:
            return Response({'success': False, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("AI endpoint error")
            return Response(
                {'success': False, 'message': 'Analysis failed. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
