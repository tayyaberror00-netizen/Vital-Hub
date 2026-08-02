from django.conf import settings
from django.views.generic import TemplateView


class AuthPageView(TemplateView):
    template_name = 'authentication/auth.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['google_oauth_client_id'] = getattr(settings, 'GOOGLE_OAUTH_CLIENT_ID', '')
        return context
