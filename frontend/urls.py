from django.urls import path
from . import views

urlpatterns = [
    path('',                  views.index),
    path('index.html',        views.index),
    path('consultation.html', views.consultation),
    path('nutrition.html',    views.nutrition),
    path('xray.html',         views.xray),
    path('report-analyzer.html', views.report_analyzer),
]
