from django.views.generic import TemplateView

index           = TemplateView.as_view(template_name='frontend/index.html')
consultation    = TemplateView.as_view(template_name='frontend/consultation.html')
nutrition       = TemplateView.as_view(template_name='frontend/nutrition.html')
xray            = TemplateView.as_view(template_name='frontend/xray.html')
report_analyzer = TemplateView.as_view(template_name='frontend/report-analyzer.html')
