from rest_framework import serializers
from .models import ProviderForm, ProviderDocument
from patients.models import Patient
from django.conf import settings
from django.core.files.base import File
from io import BytesIO
import uuid
from datetime import datetime
import os
from .pdf_utils import fill_pdf
#provider form serializer
class ProviderFormSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderForm
        fields = '__all__'
        read_only_fields = ['user', 'completed', 'date_created']
class ProviderDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderDocument
        fields = ['id', 'document_type', 'uploaded_at']
        read_only_fields = ['user', 'uploaded_at']

class DocumentUploadSerializer(serializers.Serializer):
    document_type = serializers.CharField()
    files = serializers.ListField(
        child=serializers.FileField()
    )
    
    def create(self, validated_data):
        pass

class JotFormWebhookSerializer(serializers.Serializer):
    formTitle = serializers.CharField(max_length=255, required=False)
    submissionID = serializers.CharField(max_length=100)
    content = serializers.JSONField()
class ProviderFormFillSerializer(serializers.Serializer):
    patient_id = serializers.IntegerField(write_only=True)
    form_type = serializers.CharField(write_only=True)
    form_data = serializers.DictField(write_only=True, required=False)

    def create(self, validated_data):
        pass