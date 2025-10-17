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
from utils.azure_storage import generate_sas_url, upload_to_azure_stream

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
    Webhook handler for JotForm submissions.
    1. Downloads the submitted PDF
    2. Uploads to Azure Blob Storage with proper path structure
    3. Sends email notification to admins with the form link
    4. Creates ProviderForm record in database
    """
    logger.info("=== JotForm Webhook Received ===")
    logger.info(f"Request data: {request.data}")
    
    serializer = JotFormWebhookSerializer(data=request.data)
    if not serializer.is_valid():
        logger.error(f"Invalid webhook data: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    form_data = data.get('content', {})
    
    # Extract provider email from form submission
    provider_email = form_data.get('q4_providerEmail') or form_data.get('providerEmail')
    form_name = data.get('formTitle', 'New Account Form')
    submission_id = data.get('submissionID')

    logger.info(f"Processing submission - Email: {provider_email}, ID: {submission_id}")

    if not provider_email or not submission_id:
        logger.error("Jotform webhook missing required data.")
        return Response(
            {"error": "Missing provider email or submission ID."}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    # Find the provider user
    try:
        provider = User.objects.get(email=provider_email)
        logger.info(f"Found provider: {provider.full_name} ({provider.email})")
    except User.DoesNotExist:
        logger.error(f"User with email {provider_email} not found.")
        return Response(
            {"error": "Provider not found."}, 
            status=status.HTTP_404_NOT_FOUND
        )

    try:
        # Download PDF from JotForm
        pdf_url = form_data.get('submissionPDF', f"https://www.jotform.com/pdf-submission/{submission_id}")
        logger.info(f"Downloading PDF from: {pdf_url}")
        response = requests.get(pdf_url, timeout=30)
        response.raise_for_status()
        logger.info(f"PDF downloaded successfully, size: {len(response.content)} bytes")

        # Generate file name with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_name = f"{slugify(form_name)}-{timestamp}.pdf"

        # Define Azure blob path: provider_name/onboarding/form-date-timestamp
        provider_slug = slugify(provider.full_name or provider.email.split('@')[0])
        blob_path = f"media/{provider_slug}/onboarding/{file_name}"

        logger.info(f"Uploading to Azure Blob Storage: {blob_path}")
        logger.info(f"Container: {settings.AZURE_CONTAINER}")
        logger.info(f"Content size: {len(response.content)} bytes")
        
        # Upload to Azure Blob Storage
        with BytesIO(response.content) as stream:
            upload_result = upload_to_azure_stream(stream, blob_path, settings.AZURE_CONTAINER)
            logger.info(f"Azure upload result: {upload_result}")
            
            if not upload_result:
                logger.error("⚠️ Azure upload returned False - check Azure credentials and permissions")
            else:
                logger.info("✅ Azure upload successful")

        # Create or update database record with blob path as string
        form, created = ProviderForm.objects.get_or_create(
            user=provider,
            submission_id=submission_id,
            defaults={
                'form_type': form_name,
                'completed_form': blob_path,  # Store the blob path as string
                'form_data': form_data,
                'completed': True,
            }
        )
        
        if not created:
            # Update existing record
            form.completed_form = blob_path
            form.form_data = form_data
            form.completed = True
            form.save()
            logger.info(f"Updated existing form record for submission {submission_id}")
        else:
            logger.info(f"Created new form record for submission {submission_id}")

        # Generate SAS URL for email
        try:
            sas_url = generate_sas_url(
                blob_name=blob_path,
                container_name=settings.AZURE_CONTAINER,
                permission='r'
            )
            logger.info("SAS URL generated successfully")
        except Exception as e:
            logger.warning(f"Could not generate SAS URL: {e}")
            sas_url = None

        # Send email notification to admins
        try:
            admin_emails = [email for name, email in settings.ADMINS]
            
            if not admin_emails:
                logger.warning("No admin emails configured in settings.ADMINS")
            else:
                subject = f"New Provider Application - {provider.full_name}"
                
                # Render email body
                email_body = render_to_string('email/new_provider_application.html', {
                    'provider': provider,
                    'form_name': form_name,
                    'submission_id': submission_id,
                    'sas_url': sas_url,
                    'submission_date': form.date_created.strftime('%B %d, %Y at %I:%M %p'),
                })

                email = EmailMessage(
                    subject,
                    email_body,
                    settings.DEFAULT_FROM_EMAIL,
                    admin_emails,
                )
                email.content_subtype = "html"
                email.send()
                
                logger.info(f"Email sent to admins: {admin_emails}")

        except Exception as email_error:
            logger.error(f"Failed to send email notification: {email_error}", exc_info=True)
            # Don't fail the webhook if email fails

        logger.info("=== Webhook processed successfully ===")
        
        return Response(
            {
                "success": True, 
                "message": "Form processed and saved to Azure.",
                "form_id": form.id,
                "blob_path": blob_path,
                "completed": form.completed
            }, 
            status=status.HTTP_200_OK
        )

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to download PDF from Jotform: {e}")
        return Response(
            {"error": "Failed to download PDF."}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        return Response(
            {"error": f"Internal server error: {str(e)}"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        
@csrf_exempt
@api_view(['POST', 'GET'])
@permission_classes([permissions.AllowAny])
def jotform_webhook_debug(request):
    """
    DEBUG endpoint to see exactly what JotForm sends.
    Use this temporarily to capture the webhook data.
    """
    import json
    
    try:
        # Safely extract headers
        headers = {}
        for key, value in request.META.items():
            if key.startswith('HTTP_'):
                headers[key] = value
        
        debug_info = {
            "method": request.method,
            "content_type": request.content_type,
            "headers": headers,
            "GET": dict(request.GET),
            "POST": dict(request.POST),
            "data": request.data if hasattr(request, 'data') else {},
            "body": request.body.decode('utf-8') if request.body else None,
        }
        
        # Log everything
        logger.info("=== DEBUG WEBHOOK ===")
        logger.info(json.dumps(debug_info, indent=2, default=str))
        
        return Response({
            "success": True,
            "message": "Debug data captured - check logs",
            "captured_data": debug_info
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Debug endpoint error: {e}", exc_info=True)
        return Response({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DocumentUploadView(APIView):
    """
    Handles document uploads from providers.
    Files are emailed to the supervising physician as attachments.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = DocumentUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        doc_type = serializer.validated_data['document_type']
        uploaded_files = serializer.validated_data['files']
        user = request.user

        # Get supervising physician email from settings
        physician_email = getattr(settings, 'SUPERVISING_PHYSICIAN_EMAIL', 'doctor@example.com')

        try:
            subject = f"New Documents from {user.full_name or user.email}"
            
            # Render email body
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

            # Attach all uploaded files
            for uploaded_file in uploaded_files:
                email.attach(uploaded_file.name, uploaded_file.read(), uploaded_file.content_type)

            email.send()
            logger.info(f"Documents emailed to {physician_email} from {user.email}")

            # Create tracking record
            ProviderDocument.objects.create(
                user=user,
                document_type=doc_type,
            )
            
            return Response(
                {"success": "Documents uploaded and emailed successfully."}, 
                status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(f"Document upload/email failed: {e}", exc_info=True)
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
    """
    Generates a SAS URL for a blob path.
    """
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
                    "error": "No completed JotForm submission found for this patient.",
                    "completed_form_path": None,
                    "patient_id": patient_id
                }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            logger.error(f"Error fetching ProviderForm: {e}")
            return Response(
                {"error": "Database lookup failed."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        try:
            sas_url = generate_sas_url(
                blob_name=latest_form.completed_form,
                container_name=settings.AZURE_CONTAINER,
                permission='r'
            )

            return Response({
                "sas_url": sas_url,
                "completed_form_path": latest_form.completed_form,
                "form_data": latest_form.form_data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Failed to generate SAS URL for blob {latest_form.completed_form}: {e}")
            return Response(
                {"error": "Failed to generate secure file link."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
# Add this to your onboarding_ops/views.py temporarily for debugging




# Add to urls.py:
# path('jotform/webhook/debug/', api_views.jotform_webhook_debug, name='jotform-webhook-debug'),