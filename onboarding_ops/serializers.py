# onboarding_ops/serializers.py
from rest_framework import serializers
from .models import ProviderForm, ProviderDocument
from patients.models import Patient
from django.conf import settings

# Provider form serializer (Updated)
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
    """
    Extremely permissive serializer for JotForm webhook data.
    JotForm sends data in many different formats, so we accept everything
    and parse it in the view.
    """
    # Make everything optional - we'll handle validation in the view
    formTitle = serializers.CharField(max_length=255, required=False, allow_blank=True, allow_null=True)
    submissionID = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    content = serializers.JSONField(required=False, allow_null=True)
    
    # Additional fields JotForm might send
    formID = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    ip = serializers.CharField(max_length=50, required=False, allow_blank=True, allow_null=True)
    status = serializers.CharField(max_length=50, required=False, allow_blank=True, allow_null=True)
    created_at = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    rawRequest = serializers.JSONField(required=False, allow_null=True)
    
    # Catch-all for any other fields
    class Meta:
        # Allow any additional fields
        extra_kwargs = {
            field: {'required': False} for field in ['formTitle', 'submissionID', 'content']
        }
    
    def validate(self, data):
        """
        Very permissive validation - just return what we got.
        The view will handle the actual parsing.
        """
        return data