# onboarding_ops/models.py
from django.db import models
from django.conf import settings
from patients.models import Patient
from django.utils.text import slugify
import uuid
import os

# --- PATH FUNCTIONS ---
def provider_form_upload_path(instance, filename):
    """Dynamically generates the upload path for Jotform-submitted forms."""
    provider_slug = slugify(instance.user.full_name or 'unknown-provider')
    form_type_slug = slugify(instance.form_type or 'form')
    return f'forms/{provider_slug}/{form_type_slug}/{uuid.uuid4()}-{filename}'

def provider_document_upload_path(instance, filename):
    """Dynamically generates the upload path for provider-uploaded documents."""
    provider_slug = slugify(instance.user.full_name or 'unknown-provider')
    doc_type_slug = slugify(instance.document_type or 'document')
    return f'documents/{provider_slug}/{doc_type_slug}/{uuid.uuid4()}-{filename}'

class ProviderForm(models.Model):
    """
    Model for completed forms submitted via Jotform.
    The PDF file path is stored as a string reference to Azure Blob Storage.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='submitted_forms')
    patient = models.ForeignKey(Patient, on_delete=models.SET_NULL, null=True, blank=True)
    form_type = models.CharField(max_length=100, help_text="e.g., 'New Account Form', 'IVR Report'")
    submission_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    # Changed from FileField to CharField to store Azure blob path
    completed_form = models.CharField(max_length=500, null=True, blank=True, help_text="Azure blob path to the completed form")
    completed = models.BooleanField(default=False)
    form_data = models.JSONField(null=True, blank=True, help_text="A snapshot of the form's data.")
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_created']
        indexes = [
            models.Index(fields=['user', 'form_type', 'completed']),
            models.Index(fields=['submission_id']),
        ]

    def __str__(self):
        return f'{self.form_type} for {self.user.email}'

class ProviderDocument(models.Model):
    """
    Model to track documents uploaded by the provider for emailing.
    Files are NOT stored in this system - they are emailed directly.
    """
    DOCUMENT_TYPES = [
        ('PROVIDER_RECORDS_REVIEW', 'Provider Records Review'),
        ('MISCELLANEOUS', 'Miscellaneous'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='uploaded_documents')
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f'{self.document_type} - {self.user.email}'
    

class ProviderDocument(models.Model):
    """
    Tracks document uploads from providers to physician
    Note: Actual files are NOT stored, only emailed
    This model tracks metadata for audit purposes
    """
    DOCUMENT_TYPE_CHOICES = [
        ('PROVIDER_RECORDS_REVIEW', 'Provider Records Review'),
        ('MISCELLANEOUS', 'Miscellaneous'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='provider_documents'
    )
    document_type = models.CharField(
        max_length=50,
        choices=DOCUMENT_TYPE_CHOICES,
        default='MISCELLANEOUS'
    )
    notes = models.TextField(
        blank=True,
        help_text='Internal notes about the document upload (e.g., email recipient, file count)'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Provider Document'
        verbose_name_plural = 'Provider Documents'
    
    def __str__(self):
        return f"{self.user.full_name or self.user.email} - {self.document_type} - {self.uploaded_at.strftime('%Y-%m-%d')}"