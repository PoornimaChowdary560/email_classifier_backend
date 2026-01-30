from rest_framework import serializers
from .models import Email

class EmailCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Email
        fields = ("id", "sender", "recipient", "subject", "body", "source")

class EmailSerializer(serializers.ModelSerializer):
    confidence = serializers.SerializerMethodField()

    class Meta:
        model = Email
        fields = "__all__"
        read_only_fields = ("owner", "cleaned_text", "label", "confidence", "model_version", "created_at", "updated_at")

    def get_confidence(self, obj):
        if obj.confidence is None:
            return "N/A"
        return round(obj.confidence, 3)   # keep 3 decimal places
