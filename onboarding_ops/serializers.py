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

# FIXED: JotForm Webhook Serializer - Make fields optional
class JotFormWebhookSerializer(serializers.Serializer):
    """
    Serializer for JotForm webhook data.
    JotForm can send data in different formats, so we make fields optional.
    """
    formTitle = serializers.CharField(max_length=255, required=False, allow_blank=True)
    submissionID = serializers.CharField(max_length=100, required=False, allow_blank=True)
    content = serializers.JSONField(required=False, allow_null=True)
    
    # Additional fields that JotForm might send
    formID = serializers.CharField(max_length=100, required=False, allow_blank=True)
    ip = serializers.CharField(max_length=50, required=False, allow_blank=True)
    status = serializers.CharField(max_length=50, required=False, allow_blank=True)
    created_at = serializers.CharField(max_length=100, required=False, allow_blank=True)
    
    # JotForm might send raw submission data at root level
    rawRequest = serializers.JSONField(required=False, allow_null=True)
    
    def validate(self, data):
        """
        Custom validation to handle different JotForm formats.
        JotForm can send data in multiple ways:
        1. Standard format with submissionID and content
        2. Raw format with question IDs (q1_field, q2_field, etc.)
        3. POST with form fields directly
        """
        # If we don't have submissionID or content, try to extract from rawRequest
        if not data.get('submissionID') and not data.get('content'):
            # Check if data itself contains the submission
            if 'submissionID' not in data:
                # Try to find submission ID in various formats
                for key, value in data.items():
                    if 'submission' in key.lower() and 'id' in key.lower():
                        data['submissionID'] = value
                        break
        
        return data