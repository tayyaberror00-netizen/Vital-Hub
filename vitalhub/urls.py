from django.contrib import admin
from django.urls import path, include
from frontend.api_views import ContactMessageView

urlpatterns = [
    # Django admin panel
    path('admin/', admin.site.urls),

    # ── REST API routes ──────────────────────────────────────────────
    path('api/auth/',         include('authentication.urls')),
    path('api/products/',     include('products.urls')),
    path('api/orders/',       include('orders.urls')),
    path('api/appointments/', include('appointments.urls')),
    path('api/admin/',        include('adminpanel.api_urls')),
    path('api/ai/',           include('ai.urls')),
    path('api/newsletter/',   include('frontend.api_urls')),
    path('api/contact/',      ContactMessageView.as_view()),

    # ── Custom admin panel pages ─────────────────────────────────────
    path('admin-panel/', include('adminpanel.urls')),

    # ── App-owned HTML pages ─────────────────────────────────────────
    path('', include('authentication.page_urls')),   # auth.html
    path('', include('products.page_urls')),          # store.html, product-detail.html
    path('', include('orders.page_urls')),            # checkout.html, thank-you.html
    path('', include('appointments.page_urls')),      # appointment.html

    # ── Shared / unowned frontend pages ─────────────────────────────
    path('', include('frontend.urls')),               # index, nutrition, consultation, xray
]
