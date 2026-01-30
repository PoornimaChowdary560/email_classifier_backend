from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from .models import Email
from .serializers import EmailSerializer, EmailCreateSerializer
from ml.ml_loader import predict_text
import pandas as pd
from io import TextIOWrapper
from ml.preprocess import preprocess_text
from django.db.models import Count
from django.db.models.functions import TruncDate
import csv
from django.http import HttpResponse
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from rest_framework.decorators import api_view, permission_classes


class IsOwnerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.is_authenticated and getattr(request.user, "role", "") == "admin":
            return True
        return obj.owner == request.user

class EmailViewSet(viewsets.ModelViewSet):
    queryset = Email.objects.all()
    serializer_class = EmailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # owner only unless admin wants to see all
        qs = Email.objects.all()
        if getattr(self.request.user, "role", "") != "admin":
            qs = qs.filter(owner=self.request.user)
        # filtering via query params: label, sender
        label = self.request.query_params.get("label")
        sender = self.request.query_params.get("sender")
        if label:
            qs = qs.filter(label__iexact=label)
        if sender:
            qs = qs.filter(sender__icontains=sender)
        return qs.order_by("-created_at")

    def get_serializer_class(self):
        if self.action in ("create", "bulk_upload"):
            return EmailCreateSerializer
        return EmailSerializer

    def perform_create(self, serializer):
        email = serializer.save(owner=self.request.user)
        # clean the body
        cleaned = preprocess_text(email.body)
        email.cleaned_text = cleaned

        # classify on cleaned text (not raw)
        label, confidence, meta = predict_text(cleaned)
        email.label = label
        email.confidence = confidence
        email.model_version = meta.get("model_name") or ""
        email.save()



    @action(methods=["post"], detail=False, url_path="bulk_upload")
    def bulk_upload(self, request):
        f = request.FILES.get("file")
        if not f:
            return Response({"detail": "No file uploaded."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            df = pd.read_csv(TextIOWrapper(f.file, encoding="utf-8"))
        except Exception:
            return Response({"detail": "Failed to parse CSV."}, status=status.HTTP_400_BAD_REQUEST)

        # Map columns (sender, recipient, subject, body)
        cols = [c.lower().strip() for c in df.columns]
        mapping = {}
        for c in cols:
            if "from" in c or "sender" in c: mapping["sender"] = c
            if "to" in c or "recipient" in c: mapping["recipient"] = c
            if "subject" in c: mapping["subject"] = c
            if "body" in c or "text" in c or "message" in c: mapping["body"] = c
        if "body" not in mapping: mapping["body"] = cols[-1]

        created = []
        errors = []
        with transaction.atomic():
            for i, row in df.iterrows():
                try:
                    body = str(row.get(mapping.get("body",""), ""))
                    if not body.strip(): continue
                    email = Email.objects.create(
                        owner=request.user,
                        sender=str(row.get(mapping.get("sender",""), "")),
                        recipient=str(row.get(mapping.get("recipient",""), "")),
                        subject=str(row.get(mapping.get("subject",""), "")),
                        body=body,
                        source=Email.SOURCE_CSV
                    )
                    # classify immediately
                    cleaned = preprocess_text(email.body)
                    email.cleaned_text = cleaned
                    label, confidence, meta = predict_text(cleaned)
                    email.label = label
                    email.confidence = confidence
                    email.model_version = meta.get("model_name") or ""
                    email.save()
                    created.append(email.id)
                except Exception as e:
                    errors.append({"row": int(i), "error": str(e)})
        return Response({"created": len(created), "ids": created, "errors": errors})


    @action(methods=["post"], detail=True, url_path="reclassify")
    def reclassify(self, request, pk=None):
        """
        Manually reclassify an email (user corrected label).
        Body: { "label": "Ham" }
        """
        email = self.get_object()
        if email.owner != request.user and getattr(request.user, "role", "") != "admin":
            return Response({"detail":"Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        new_label = request.data.get("label")
        if not new_label:
            return Response({"detail":"label required"}, status=status.HTTP_400_BAD_REQUEST)
        email.label = new_label
        email.save()
        return Response({"detail":"updated", "label": email.label})

@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def label_distribution(request):
    data = Email.objects.values("label").annotate(count=Count("id"))
    return Response({item["label"]: item["count"] for item in data})

@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def spam_trend(request):
    data = (
        Email.objects.annotate(date=TruncDate("created_at"))
        .values("date", "label")
        .annotate(count=Count("id"))
        .order_by("date")
    )
    # Format into spam/ham per day
    result = {}
    for item in data:
        date = str(item["date"])
        if date not in result:
            result[date] = {"spam": 0, "ham": 0}
        result[date][item["label"]] = item["count"]
    return Response(result)

@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def export_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="emails.csv"'

    writer = csv.writer(response)
    writer.writerow(["Sender", "Recipient", "Subject", "Label", "Confidence"])
    for email in Email.objects.all():
        writer.writerow([email.sender, email.recipient, email.subject, email.label, email.confidence])

    return response

@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def export_pdf(request):
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="report.pdf"'

    doc = SimpleDocTemplate(response)
    styles = getSampleStyleSheet()
    content = []

    spam_count = Email.objects.filter(label="Spam").count()
    ham_count = Email.objects.filter(label="Ham").count()

    content.append(Paragraph("Email Classification Report", styles["Heading1"]))
    content.append(Paragraph(f"Spam Emails: {spam_count}", styles["Normal"]))
    content.append(Paragraph(f"Ham Emails: {ham_count}", styles["Normal"]))

    doc.build(content)
    return response