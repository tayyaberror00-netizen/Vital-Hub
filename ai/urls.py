from django.urls import path
from .views import (
    NutritionView, XrayView, ConsultationChatView,
    NutritionPlanView, GroceryListView, ReportAnalyzerView,
)

urlpatterns = [
    path('nutrition/',           NutritionView.as_view()),
    path('xray/',                XrayView.as_view()),
    path('consultation-chat/',   ConsultationChatView.as_view()),
    path('nutrition-plan/',      NutritionPlanView.as_view()),
    path('grocery-list/',        GroceryListView.as_view()),
    path('report-analyzer/',     ReportAnalyzerView.as_view()),
]
