# onboarding_ops/serializers.py
from rest_framework import serializers
from .models import ProviderForm, ProviderDocument
from patients.models import Patient
from django.conf import settings


# Provider form serializer
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


# Provider Document serializer - Updated with more fields
class ProviderDocumentSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = ProviderDocument
        fields = [
            'id',
            'user',
            'user_name',
            'user_email',
            'document_type',
            'notes',
            'uploaded_at',
        ]
        read_only_fields = ['id', 'user', 'uploaded_at']


# Document Upload serializer - Enhanced with validation
class DocumentUploadSerializer(serializers.Serializer):
    """
    Serializer for handling multiple file uploads
    Files are validated and prepared for email attachment
    """
    document_type = serializers.ChoiceField(
        choices=[
            ('PROVIDER_RECORDS_REVIEW', 'Provider Records Review'),
            ('MISCELLANEOUS', 'Miscellaneous'),
        ],
        required=True
    )
    
    files = serializers.ListField(
        child=serializers.FileField(
            max_length=100000,
            allow_empty_file=False,
            use_url=False
        ),
        allow_empty=False,
        min_length=1,
        max_length=10,  # Maximum 10 files per upload
        required=True
    )

    def validate_files(self, files):
        """
        Validate file extensions and sizes
        """
        allowed_extensions = ['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'gif']
        max_size = 10 * 1024 * 1024  # 10MB per file
        
        for file in files:
            # Check extension
            ext = file.name.split('.')[-1].lower()
            if ext not in allowed_extensions:
                raise serializers.ValidationError(
                    f"File '{file.name}' has unsupported extension. "
                    f"Allowed: {', '.join(allowed_extensions)}"
                )
            
            # Check size
            if file.size > max_size:
                raise serializers.ValidationError(
                    f"File '{file.name}' is too large. Maximum size is 10MB."
                )
        
        return files

    def create(self, validated_data):
        # This method is not implemented because files are handled in the view
        # Files are emailed, not stored
        pass


# JotForm Webhook serializer
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