from django.db import models
from django.conf import settings

class Email(models.Model):
    SOURCE_MANUAL = "manual"
    SOURCE_CSV = "csv"
    SOURCE_GMAIL = "gmail"
    SOURCE_CHOICES = [
        (SOURCE_MANUAL, "Manual"),
        (SOURCE_CSV, "CSV"),
        (SOURCE_GMAIL, "Gmail"),
    ]

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="emails")
    sender = models.CharField(max_length=320, blank=True)   # email max length
    recipient = models.CharField(max_length=320, blank=True)
    subject = models.CharField(max_length=1024, blank=True)
    body = models.TextField()                # raw body
    cleaned_text = models.TextField(blank=True, null=True)
    label = models.CharField(max_length=50, blank=True)  # 'Spam'/'Ham' or categories
    confidence = models.FloatField(null=True, blank=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default=SOURCE_MANUAL)
    model_version = models.CharField(max_length=100, blank=True)  # store model id/version used
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.subject or '[no-subject]'} - {self.sender} ({self.label})"
