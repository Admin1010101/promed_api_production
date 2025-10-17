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
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request data: {request.data}")
    logger.info(f"Request POST: {request.POST}")
    logger.info(f"Request body: {request.body[:500] if request.body else 'No body'}")
    
    # JotForm sends data in different formats, try to handle all
    raw_data = request.data if request.data else request.POST.dict()
    
    serializer = JotFormWebhookSerializer(data=raw_data)
    if not serializer.is_valid():
        logger.error(f"Invalid webhook data: {serializer.errors}")
        logger.error(f"Received data: {raw_data}")
        # Don't fail - try to extract what we need manually
        data = raw_data
        form_data = raw_data
    else:
        data = serializer.validated_data
        form_data = data.get('content', raw_data)
    
    # Extract provider email from form submission
    provider_email = form_data.get('q4_providerEmail') or form_data.get('providerEmail')
    form_name = data.get('formTitle', 'New Account Form')
    submission_id = data.get('submissionID')

    if not provider_email or not submission_id:
        logger.error("Jotform webhook missing required data.")
        return Response(
            {"error": "Missing provider email or submission ID."}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    # Find the provider user
    try:
        provider = User.objects.get(email=provider_email)
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
        response = requests.get(pdf_url)
        response.raise_for_status()

        # Generate file name with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_name = f"{slugify(form_name)}-{timestamp}.pdf"

        # Define Azure blob path: provider_name/patient_name/form-date-timestamp
        provider_slug = slugify(provider.full_name or provider.email.split('@')[0])
        
        # For new account forms, there's no patient yet, so use 'onboarding'
        blob_path = f"media/{provider_slug}/onboarding/{file_name}"

        # Upload to Azure Blob Storage
        logger.info(f"Uploading to Azure: {blob_path}")
        with BytesIO(response.content) as stream:
            upload_to_azure_stream(stream, blob_path, settings.AZURE_CONTAINER)

        # Create or update database record
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
        except Exception as e:
            logger.warning(f"Could not generate SAS URL: {e}")
            sas_url = None

        # Send email notification to admins
        try:
            admin_emails = [email for name, email in settings.ADMINS]
            
            if not admin_emails:
                logger.warning("No admin emails configured in settings.ADMINS")
            else:
                subject = "Completed New Provider Application"
                
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

        return Response(
            {
                "success": True, 
                "message": "Form processed and saved to Azure.",
                "form_id": form.id,
                "blob_path": blob_path
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