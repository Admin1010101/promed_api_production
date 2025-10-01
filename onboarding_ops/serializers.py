from rest_framework import serializers
from .models import ProviderForm, ProviderDocument
from patients.models import Patient
from django.conf import settings

# provider form serializer (Updated)
class ProviderFormSerializer(serializers.ModelSerializer):
    patient_full_name = serializers.CharField(source='patient.full_name', read_only=True)

    class Meta:
        model = ProviderForm
        fields = [
            'id', 'user', 'patient', 'patient_full_name',
            'form_type', 'submission_id', 'completed_form',
            'form_data', 'date_created', 'completed'
        ]
        read_only_fields = ['user', 'patient', 'submission_id', 'completed_form', 'completed', 'date_created', 'form_data']

# Provider Document serializer (No Change)
class ProviderDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderDocument
        fields = ['id', 'document_type', 'uploaded_at']
        read_only_fields = ['user', 'uploaded_at']

# Document Upload serializer (No Change)
class DocumentUploadSerializer(serializers.Serializer):
    document_type = serializers.CharField()
    files = serializers.ListField(
        child=serializers.FileField()
    )

    def create(self, validated_data):
        # This method is not implemented because files are handled in the view
        pass

class JotFormWebhookSerializer(serializers.Serializer):
    formTitle = serializers.CharField(max_length=255, required=False)
    submissionID = serializers.CharField(max_length=100)
    content = serializers.JSONField()

