import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

logger = logging.getLogger('vitalhub')

def _first_error(errors):
    """Flatten DRF serializer.errors into one human-readable message."""
    for field, msgs in errors.items():
        msg = msgs[0] if isinstance(msgs, list) else msgs
        return f"{field}: {msg}"
    return "Invalid request."


def _quota_response(e):
    """Standard 429 payload for a quota-exceeded error, consumed by the
    frontend to show a friendly 'weekly limit reached' modal."""
    return Response({
        'success': False,
        'quota_exceeded': True,
        'limit': e.limit,
        'message': f"You've reached your weekly limit of {e.limit} for this feature. "
                   f"It resets 7 days after each use — upgrade or check back soon.",
    }, status=status.HTTP_429_TOO_MANY_REQUESTS)


from .serializers import (
    NutritionInputSerializer, ConsultationChatSerializer,
    NutritionPlanSerializer, GroceryListSerializer,
)
from .services import (
    NutritionService, XrayService, ConsultationService,
    NutritionPlanService, ReportAnalyzerService,
    UsageQuotaService, QuotaExceededError,
)


class NutritionView(APIView):
    # Legacy BMR-only calculator — not called by the current frontend, kept
    # public/unauthenticated since it predates the quota system.
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
    # Protected feature — requires login, and normal users are capped at
    # UsageQuotaService.WEEKLY_LIMITS['xray_scan'] scans / 7 days. Admins
    # are exempt.
    permission_classes = [IsAuthenticated]
    parser_classes     = [MultiPartParser, FormParser]

    def post(self, request):
        image = request.FILES.get('image')
        if not image:
            return Response(
                {'success': False, 'message': 'No image file provided.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            UsageQuotaService.check(request.user, 'xray_scan')
        except QuotaExceededError as e:
            return _quota_response(e)

        try:
            result = XrayService.analyze(image)
            UsageQuotaService.log_usage(request.user, 'xray_scan', detail=image.name)
            return Response({'success': True, **result})
        except ValueError as e:
            return Response(
                {'success': False, 'message': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception:
            logger.exception("AI endpoint error")
            return Response(
                {'success': False, 'message': 'Analysis failed. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ConsultationChatView(APIView):
    # Public per product spec — the AI Assistant chat stays open to everyone,
    # logged in or not.
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
    # Protected feature — requires login, capped at 3 plans / 7 days for
    # normal users. Admins are exempt.
    permission_classes = [IsAuthenticated]
    parser_classes     = [JSONParser]

    def post(self, request):
        serializer = NutritionPlanSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'errors': serializer.errors, 'message': _first_error(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            UsageQuotaService.check(request.user, 'nutrition_plan')
        except QuotaExceededError as e:
            return _quota_response(e)

        try:
            plan = NutritionPlanService.generate_week_plan(serializer.validated_data)
            UsageQuotaService.log_usage(
                request.user, 'nutrition_plan',
                detail=f"goal={serializer.validated_data.get('goal')}",
            )
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
    # Protected (same gate as the nutrition plan it's derived from), but not
    # separately quota-limited — generating a plan already consumed the quota.
    permission_classes = [IsAuthenticated]
    parser_classes     = [JSONParser]

    def post(self, request):
        serializer = GroceryListSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'errors': serializer.errors, 'message': _first_error(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)
        try:
            groceries = NutritionPlanService.generate_grocery_list(
                serializer.validated_data['week_plan'],
                budget=serializer.validated_data.get('budget', False),
            )
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
    # Protected feature — requires login, capped at
    # UsageQuotaService.WEEKLY_LIMITS['report_scan'] scans / 7 days. Admins
    # are exempt.
    permission_classes = [IsAuthenticated]
    parser_classes     = [MultiPartParser, FormParser]

    def post(self, request):
        report_file = request.FILES.get('report')
        if not report_file:
            return Response({'success': False, 'message': 'No report file provided.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            UsageQuotaService.check(request.user, 'report_scan')
        except QuotaExceededError as e:
            return _quota_response(e)

        try:
            result = ReportAnalyzerService.analyze(report_file)
            UsageQuotaService.log_usage(request.user, 'report_scan', detail=report_file.name)
            return Response({'success': True, **result})
        except ValueError as e:
            return Response({'success': False, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("AI endpoint error")
            return Response(
                {'success': False, 'message': 'Analysis failed. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
