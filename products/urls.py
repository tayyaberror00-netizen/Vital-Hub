from django.urls import path
from .views import ProductListView, ProductDetailView, ProductLikeView, LikedProductsView

urlpatterns = [
    path('',                          ProductListView.as_view()),
    path('liked/',                    LikedProductsView.as_view()),
    path('<str:product_id>/',         ProductDetailView.as_view()),
    path('<str:product_id>/like/',    ProductLikeView.as_view()),
]
