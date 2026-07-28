from django.urls import path
from .api_views import NewsletterSubscribeView

urlpatterns = [
    path('subscribe/', NewsletterSubscribeView.as_view()),
]
