from django.urls import path
from .views import invoice_report, project_dashboard

urlpatterns = [
    path("invoice/<int:invoice_id>/", invoice_report, name="invoice_report"),
    path("project/<int:project_id>/", project_dashboard, name="project_dashboard"),
]