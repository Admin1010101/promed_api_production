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
from io import BytesIO
from xhtml2pdf import pisa
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
# DocumentUploadView (Updated POST method)

class DocumentUploadView(APIView):
    """Handles document uploads from providers."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # 🟢 ASSUMES: DocumentUploadSerializer now includes 'message' field
        serializer = DocumentUploadSerializer(data=request.data) 
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        doc_type = serializer.validated_data['document_type']
        uploaded_files = serializer.validated_data['files']
        # 🟢 NEW: Get the message from the serializer
        provider_message = serializer.validated_data.get('message', '') 
        user = request.user

        physician_email = getattr(settings, 'SUPERVISING_PHYSICIAN_EMAIL', 'doctor@example.com')

        try:
            subject = f"New Documents from {user.full_name or user.email}"
            
            # Get list of file names for the email template
            file_names = [f.name for f in uploaded_files]
            
            body = render_to_string('email/document_upload.html', {
                'user': user,
                'document_type': doc_type,
                'file_count': len(uploaded_files),
                # 🟢 NEW: Pass the message to the email template
                'provider_message': provider_message,
                # 🟢 NEW: Pass file names to the email template
                'file_names': file_names, 
                'provider_name': user.full_name or user.email, # Ensure name is passed
                'provider_email': user.email,
                'submission_date': timezone.now().strftime("%B %d, %Y"), # Pass the date
            })

            # ... (EmailMessage setup remains the same)
            email = EmailMessage(
                subject,
                body,
                settings.DEFAULT_FROM_EMAIL,
                [physician_email],
            )
            email.content_subtype = "html"

            for uploaded_file in uploaded_files:
                email.attach(uploaded_file.name, uploaded_file.read(), uploaded_file.content_type)
            # ... (rest of the email logic and response remains the same)
            
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

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def save_new_account_form(request):
    """
    Save new account form as PDF to Azure Blob Storage using xhtml2pdf
    """
    if not request.user or not request.user.is_authenticated:
        return Response(
            {"error": "Authentication failed. User not found."},
            status=status.HTTP_401_UNAUTHORIZED # Use 401
        )
    try:
        form_data = request.data.get('form_data', {})
        
        # Prepare data for template
        context = {
            'provider': request.user,
            'form_data': form_data,
            'submission_date': datetime.now().strftime('%B %d, %Y')
        }
        
        # Render HTML template
        html_string = render_to_string('onboarding_ops/new_account_form_submission.html', context)
        
        # Generate PDF using xhtml2pdf
        pdf_buffer = BytesIO()
        pisa_status = pisa.CreatePDF(
            html_string,
            dest=pdf_buffer,
            encoding='utf-8'
        )
        
        if pisa_status.err:
            logger.error(f"PDF generation error: {pisa_status.err}")
            return Response({
                "success": False,
                "error": "Failed to generate PDF"
            }, status=500)
        
        pdf_content = pdf_buffer.getvalue()
        pdf_buffer.close()
        
        # Create blob path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        provider_slug = slugify(request.user.full_name or request.user.email.split('@')[0])
        file_name = f"new_account_form_{timestamp}.pdf"
        blob_path = f"onboarding_forms/{provider_slug}/{file_name}"
        
        # Upload to Azure
        blob_service_client = BlobServiceClient.from_connection_string(
            settings.AZURE_STORAGE_CONNECTION_STRING
        )
        blob_client = blob_service_client.get_blob_client(
            container=settings.AZURE_MEDIA_CONTAINER,
            blob=blob_path
        )
        blob_client.upload_blob(pdf_content, overwrite=True)
        
        # Verify upload
        if not blob_client.exists():
            logger.error("Blob upload verification failed")
            return Response({
                "success": False,
                "error": "Failed to verify file upload"
            }, status=500)
        
        # Save to database
        provider_form = ProviderForm.objects.create(
            user=request.user,
            form_type='New Account Form',
            completed_form=blob_path,
            form_data=form_data,
            completed=True
        )
        
        # Generate SAS URL
        from utils.azure_storage import generate_sas_url
        sas_url = generate_sas_url(blob_path, settings.AZURE_MEDIA_CONTAINER, 'r', 72)
        
        # ✅ UPDATED: Send email to BOTH admins AND provider
        try:
            admin_emails = [email for name, email in settings.ADMINS]
            provider_email = request.user.email
            
            # Combine and remove duplicates
            recipient_list = list(set(admin_emails + [provider_email]))
            
            if recipient_list:
                subject = f"New Account Form Submitted - {request.user.full_name}"
                email_body = render_to_string('email/new_account_form_submission.html', {
                    'provider': request.user,
                    'form_data': form_data,
                    'sas_url': sas_url,
                    'submission_date': datetime.now().strftime('%B %d, %Y at %I:%M %p'),
                })
                email = EmailMessage(
                    subject, 
                    email_body, 
                    settings.DEFAULT_FROM_EMAIL, 
                    recipient_list
                )
                email.content_subtype = "html"
                email.send()
                
                logger.info(f"✅ Email sent to {len(recipient_list)} recipients: {', '.join(recipient_list)}")
        except Exception as e:
            logger.warning(f"⚠️ Email failed: {str(e)}")
        
        return Response({
            "success": True,
            "form_id": provider_form.id,
            "blob_path": blob_path,
            "sas_url": sas_url,
            "date_created": provider_form.date_created.isoformat(),
            "message": "Form saved successfully"
        }, status=201)
        
    except Exception as e:
        logger.error(f"Error saving new account form: {str(e)}", exc_info=True)
        return Response({
            "success": False,
            "error": str(e)
        }, status=500)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def check_new_account_form_status(request):
    """
    Check if the current user has completed a new account form
    """
    try:
        # Get the most recent completed new account form
        form = ProviderForm.objects.filter( 
            user=request.user,
            form_type='New Account Form',
            completed=True
        ).order_by('-date_created').first()
        
        if form:
            # Generate SAS URL
            from utils.azure_storage import generate_sas_url
            sas_url = generate_sas_url(
                form.completed_form, 
                settings.AZURE_MEDIA_CONTAINER, 
                'r', 
                72
            )
            
            return Response({
                "completed": True,
                "form_id": form.id,
                "date_created": form.date_created.isoformat(),
                "sas_url": sas_url,
                "form_data": form.form_data
            }, status=200)
        else:
            return Response({
                "completed": False
            }, status=200)
            
    except Exception as e:
        logger.error(f"Error checking form status: {str(e)}", exc_info=True)
        return Response({
            "success": False,
            "error": str(e)
        }, status=500)