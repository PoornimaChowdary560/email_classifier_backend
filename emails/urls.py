from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EmailViewSet, label_distribution, spam_trend, export_csv, export_pdf

router = DefaultRouter()
router.register(r"", EmailViewSet, basename="emails")

urlpatterns = [
    # reports first
    path("reports/distribution/", label_distribution, name="label-distribution"),
    path("reports/trend/", spam_trend, name="spam-trend"),
    path("reports/export/csv/", export_csv, name="export-csv"),
    path("reports/export/pdf/", export_pdf, name="export-pdf"),

    # then include router
    path("", include(router.urls)),
]
