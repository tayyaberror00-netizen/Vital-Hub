from django.shortcuts import redirect
from django.views.generic import TemplateView


class AdminRequiredMixin:
    """Server-side guard: requires an active admin session (set by LoginView)."""

    def dispatch(self, request, *args, **kwargs):
        if not request.session.get('vh_is_admin'):
            return redirect('/auth.html?next=' + request.path)
        return super().dispatch(request, *args, **kwargs)


class AdminPageView(AdminRequiredMixin, TemplateView):
    pass


dashboard    = AdminPageView.as_view(template_name='adminpanel/dashboard.html')
products     = AdminPageView.as_view(template_name='adminpanel/products.html')
orders       = AdminPageView.as_view(template_name='adminpanel/orders.html')
appointments = AdminPageView.as_view(template_name='adminpanel/appointments.html')
