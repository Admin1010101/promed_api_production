# onboarding_ops/views.py
import os
import logging
from io import BytesIO
from datetime import datetime

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from django.views.decorators.csrf import csrf_exempt

from django.utils.text import slugify
from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.shortcuts import get_object_or_404
import requests
from azure.storage.blob import BlobServiceClient

from patients.models import Patient
from provider_auth.models import User
from .models import ProviderForm, ProviderDocument
from .serializers import (
    ProviderFormSerializer,
    ProviderDocumentSerializer,
    JotFormWebhookSerializer,
    DocumentUploadSerializer
)

logger = logging.getLogger(__name__)

class IsOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user

class ProviderFormListCreate(generics.ListCreateAPIView):
    serializer_class = ProviderFormSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ProviderForm.objects.filter(user=self.request.user)

class ProviderFormDetail(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProviderFormSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return ProviderForm.objects.none()
        return ProviderForm.objects.filter(user=self.request.user)

@csrf_exempt
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def jotform_webhook(request):
    """
    Webhook with detailed response for debugging.
    Returns step-by-step progress in the response.
    """
    debug_info = []
    
    def log(msg, level="INFO"):
        debug_info.append(f"[{level}] {msg}")
        logger.info(msg)
    
    try:
        log("🎯 Webhook received")
        
        # Validate request
        serializer = JotFormWebhookSerializer(data=request.data)
        if not serializer.is_valid():
            log(f"Serializer errors: {serializer.errors}", "ERROR")
            return Response({
                "success": False,
                "error": "Invalid data",
                "details": serializer.errors,
                "debug": debug_info
            }, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        form_data = data.get('content', {})
        
        # Extract data
        provider_email = (
            form_data.get('q4_providerEmail') or 
            form_data.get('providerEmail') or
            form_data.get('q3_email') or
            form_data.get('email') or
            form_data.get('contactEmail')
        )
        form_name = data.get('formTitle', 'New Account Form')
        submission_id = data.get('submissionID')
        
        log(f"Provider: {provider_email}")
        log(f"Form: {form_name}")
        log(f"Submission: {submission_id}")

        if not provider_email or not submission_id:
            log("Missing required fields", "ERROR")
            return Response({
                "success": False,
                "error": "Missing provider email or submission ID",
                "debug": debug_info
            }, status=400)

        # Find provider
        try:
            provider = User.objects.get(email=provider_email)
            log(f"✅ Provider found: {provider.full_name}")
        except User.DoesNotExist:
            log(f"Provider not found: {provider_email}", "ERROR")
            return Response({
                "success": False,
                "error": "Provider not found",
                "debug": debug_info
            }, status=404)

        # Download PDF
        pdf_url = form_data.get('submissionPDF', f"https://www.jotform.com/pdf-submission/{submission_id}")
        log(f"Downloading PDF from: {pdf_url}")
        
        try:
            response = requests.get(pdf_url, timeout=30)
            response.raise_for_status()
            pdf_size = len(response.content)
            log(f"✅ PDF downloaded: {pdf_size} bytes")
        except Exception as e:
            log(f"PDF download failed: {str(e)}", "ERROR")
            return Response({
                "success": False,
                "error": "Failed to download PDF",
                "details": str(e),
                "debug": debug_info
            }, status=500)

        if pdf_size == 0:
            log("PDF is empty", "ERROR")
            return Response({
                "success": False,
                "error": "PDF is empty",
                "debug": debug_info
            }, status=500)

        # Generate blob path
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_name = f"{slugify(form_name)}-{timestamp}.pdf"
        provider_slug = slugify(provider.full_name or provider.email.split('@')[0])
        blob_path = f"{provider_slug}/onboarding/{file_name}"
        container_name = settings.AZURE_MEDIA_CONTAINER
        
        log(f"Blob path: {blob_path}")
        log(f"Container: {container_name}")
        
        # Check Azure config
        conn_str = settings.AZURE_STORAGE_CONNECTION_STRING
        if not conn_str:
            log("Azure connection string not configured", "ERROR")
            return Response({
                "success": False,
                "error": "Azure storage not configured",
                "debug": debug_info
            }, status=500)
        
        log(f"Connection string length: {len(conn_str)}")
        
        # Upload to Azure
        try:
            log("Creating BlobServiceClient...")
            from azure.storage.blob import BlobServiceClient
            blob_service_client = BlobServiceClient.from_connection_string(conn_str)
            log("✅ BlobServiceClient created")
            
            log("Creating BlobClient...")
            blob_client = blob_service_client.get_blob_client(
                container=container_name,
                blob=blob_path
            )
            log("✅ BlobClient created")
            
            log(f"Uploading {pdf_size} bytes...")
            blob_client.upload_blob(response.content, overwrite=True)
            log("✅ Upload blob completed")
            
            # Verify
            log("Verifying blob exists...")
            if blob_client.exists():
                log("✅ BLOB VERIFIED IN AZURE!")
                blob_verified = True
            else:
                log("⚠️ Blob uploaded but exists() returned False", "WARNING")
                blob_verified = False
                
        except Exception as e:
            log(f"Azure upload error: {type(e).__name__}: {str(e)}", "ERROR")
            import traceback
            log(f"Traceback: {traceback.format_exc()}", "ERROR")
            return Response({
                "success": False,
                "error": "Azure upload failed",
                "error_type": type(e).__name__,
                "error_message": str(e),
                "debug": debug_info
            }, status=500)

        # Save to database
        try:
            log("Saving to database...")
            form, created = ProviderForm.objects.get_or_create(
                user=provider,
                submission_id=submission_id,
                defaults={
                    'form_type': form_name,
                    'completed_form': blob_path,
                    'form_data': form_data,
                    'completed': True,
                }
            )
            
            if not created:
                form.completed_form = blob_path
                form.form_data = form_data
                form.completed = True
                form.save()
                log(f"✅ Updated form record {form.id}")
            else:
                log(f"✅ Created form record {form.id}")
                
        except Exception as e:
            log(f"Database error: {str(e)}", "ERROR")
            return Response({
                "success": False,
                "error": "Database save failed",
                "details": str(e),
                "debug": debug_info
            }, status=500)

        # Generate SAS URL
        sas_url = None
        try:
            log("Generating SAS URL...")
            from utils.azure_storage import generate_sas_url
            sas_url = generate_sas_url(blob_path, container_name, 'r', 72)
            log("✅ SAS URL generated")
        except Exception as e:
            log(f"SAS URL generation failed: {str(e)}", "WARNING")

        # Send email
        try:
            log("Sending email...")
            admin_emails = [email for name, email in settings.ADMINS]
            
            if admin_emails:
                subject = f"New Provider Application - {provider.full_name}"
                email_body = render_to_string('email/new_provider_application.html', {
                    'provider': provider,
                    'form_name': form_name,
                    'submission_id': submission_id,
                    'sas_url': sas_url,
                    'submission_date': form.date_created.strftime('%B %d, %Y at %I:%M %p'),
                })
                email = EmailMessage(subject, email_body, settings.DEFAULT_FROM_EMAIL, admin_emails)
                email.content_subtype = "html"
                email.send()
                log(f"✅ Email sent to {len(admin_emails)} recipients")
            else:
                log("No admin emails configured", "WARNING")
                
        except Exception as e:
            log(f"Email failed: {str(e)}", "WARNING")

        log("✅ WEBHOOK COMPLETED SUCCESSFULLY")
        
        # Return detailed success response
        return Response({
            "success": True,
            "message": "Form processed and saved to Azure",
            "data": {
                "form_id": form.id,
                "blob_path": blob_path,
                "container": container_name,
                "file_size": pdf_size,
                "blob_verified": blob_verified,
                "provider_email": provider_email,
                "submission_id": submission_id,
                "sas_url_generated": sas_url is not None
            },
            "debug": debug_info
        }, status=200)

    except Exception as e:
        log(f"FATAL ERROR: {type(e).__name__}: {str(e)}", "ERROR")
        import traceback
        log(f"Traceback: {traceback.format_exc()}", "ERROR")
        
        return Response({
            "success": False,
            "error": "Internal server error",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "debug": debug_info
        }, status=500)
        
@csrf_exempt
@api_view(['POST', 'GET'])
@permission_classes([permissions.AllowAny])
def jotform_webhook_debug(request):
    """Simple debug endpoint"""
    try:
        return Response({
            "success": True,
            "method": request.method,
            "content_type": request.content_type,
            "GET_params": dict(request.GET),
            "POST_data": dict(request.POST),
            "request_data": request.data,
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Debug error: {e}", exc_info=True)
        return Response({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DocumentUploadView(APIView):
    """Handles document uploads from providers."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = DocumentUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        doc_type = serializer.validated_data['document_type']
        uploaded_files = serializer.validated_data['files']
        user = request.user

        physician_email = getattr(settings, 'SUPERVISING_PHYSICIAN_EMAIL', 'doctor@example.com')

        try:
            subject = f"New Documents from {user.full_name or user.email}"
            
            body = render_to_string('email/document_upload.html', {
                'user': user,
                'document_type': doc_type,
                'file_count': len(uploaded_files),
            })

            email = EmailMessage(
                subject,
                body,
                settings.DEFAULT_FROM_EMAIL,
                [physician_email],
            )
            email.content_subtype = "html"

            for uploaded_file in uploaded_files:
                email.attach(uploaded_file.name, uploaded_file.read(), uploaded_file.content_type)

            email.send()

            ProviderDocument.objects.create(
                user=user,
                document_type=doc_type,
            )
            
            return Response(
                {"success": "Documents uploaded and emailed successfully."}, 
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CheckBlobExistsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, container_name, blob_name, *args, **kwargs):
        try:
            blob_service_client = BlobServiceClient.from_connection_string(
                settings.AZURE_STORAGE_CONNECTION_STRING
            )
            container_client = blob_service_client.get_container_client(container_name)
            blob_client = container_client.get_blob_client(blob_name)

            if blob_client.exists():
                return Response({'exists': True}, status=status.HTTP_200_OK)
            else:
                return Response({'exists': False}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ProviderDocumentListCreate(generics.ListCreateAPIView):
    serializer_class = ProviderDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ProviderDocument.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class ProviderDocumentDetail(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProviderDocumentSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return ProviderDocument.objects.none()
        
        return ProviderDocument.objects.filter(user=self.request.user)

class GenerateSASURLView(APIView):
    """Generates a SAS URL for a blob path."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        patient_id = request.query_params.get('patient_id')
        form_type = request.query_params.get('form_type')

        if not patient_id or not form_type:
            return Response(
                {"error": "Missing patient_id or form_type query parameter."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            patient = get_object_or_404(Patient, pk=patient_id)
            latest_form = ProviderForm.objects.filter(
                user=request.user,
                patient=patient,
                form_type__iexact=form_type,
                completed=True
            ).order_by('-date_created').first()

            if not latest_form or not latest_form.completed_form:
                return Response({
                    "error": "No completed JotForm submission found for this patient."
                }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response(
                {"error": "Database lookup failed."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        try:
            from utils.azure_storage import generate_sas_url
            sas_url = generate_sas_url(
                blob_name=latest_form.completed_form,
                container_name=settings.AZURE_MEDIA_CONTAINER,
                permission='r'
            )

            return Response({
                "sas_url": sas_url,
                "completed_form_path": latest_form.completed_form,
                "form_data": latest_form.form_data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": "Failed to generate secure file link."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )