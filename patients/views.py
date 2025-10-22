# patients/views.py
import logging
import json
from datetime import datetime
from django.conf import settings
from django.utils.text import slugify
from django.template.loader import render_to_string 
from django.core.mail import EmailMessage
from io import BytesIO 

# Import pisa for PDF generation
from xhtml2pdf import pisa 

from rest_framework import generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from . import serializers as api_serializers

from azure.storage.blob import BlobServiceClient
from azure.storage.blob import ContentSettings 

from patients.models import Patient
from onboarding_ops.models import ProviderForm
from utils.azure_storage import generate_sas_url 
from provider_auth.models import User

logger = logging.getLogger(__name__)

# --- ViewSets remain unchanged ---

class PatientListView(generics.ListCreateAPIView):
    serializer_class = api_serializers.PatientSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Patient.objects.none()
        
        if self.request.user.is_authenticated:
            queryset = Patient.objects.filter(provider=self.request.user)
            logger.info(f"PatientListView - Found {queryset.count()} patients")
            return queryset
        
        logger.warning("PatientListView - Unauthenticated request")
        return Patient.objects.none()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        logger.info(f"PatientListView - Returning {len(serializer.data)} patients")
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """Override create to add better error handling and logging"""
        logger.info("="*50)
        logger.info("🔍 PATIENT CREATION REQUEST")
        logger.info(f"User: {request.user.email} (ID: {request.user.id})")
        logger.info(f"Raw request data keys: {list(request.data.keys())}")
        logger.info("="*50)
        
        try:
            # Make a mutable copy of the data and remove provider fields
            data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
            
            # Remove any provider-related fields that shouldn't be in the request
            data.pop('provider', None)
            data.pop('provider_id', None)
            
            logger.info(f"Cleaned data keys: {list(data.keys())}")
            
            # Create serializer with cleaned data
            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            
            # Perform the create
            self.perform_create(serializer)
            
            headers = self.get_success_headers(serializer.data)
            logger.info(f"✅ Patient created successfully: {serializer.data.get('id')}")
            
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
            
        except Exception as e:
            logger.error(f"❌ Error creating patient: {str(e)}", exc_info=True)
            
            return Response(
                {
                    'error': str(e),
                    'detail': 'An error occurred while creating the patient'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def perform_create(self, serializer):
        logger.info("="*50)
        logger.info("🔍 PERFORM CREATE")
        logger.info(f"User ID: {self.request.user.id}")
        logger.info(f"User Email: {self.request.user.email}")
        
        # Check if user exists in correct table
        user_exists = User.objects.filter(id=self.request.user.id).exists()
        logger.info(f"User exists in provider_auth.User: {user_exists}")
        
        if user_exists:
            user_obj = User.objects.get(id=self.request.user.id)
            logger.info(f"User from DB: {user_obj.email} (ID: {user_obj.id})")
        
        logger.info("="*50)
        
        try:
            validated_data = serializer.validated_data
            validated_data.pop('provider', None)
            validated_data.pop('provider_id', None)
            
            # Save with the current user as provider
            patient = serializer.save(provider=self.request.user)
            logger.info(f"✅ Patient created with ID: {patient.id}")
            logger.info(f"✅ Patient provider ID: {patient.provider_id}")
            logger.info(f"✅ Patient provider email: {patient.provider.email}")
            
        except Exception as e:
            logger.error(f"❌ Error in perform_create: {str(e)}", exc_info=True)
            raise


class PatientDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = api_serializers.PatientSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Patient.objects.none()
        
        if self.request.user.is_authenticated:
            return Patient.objects.filter(provider=self.request.user)
        
        return Patient.objects.none()
    
    def update(self, request, *args, **kwargs):
        """Override update to add better error handling"""
        try:
            # Remove provider fields from update data
            data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
            data.pop('provider', None)
            data.pop('provider_id', None)
            
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"❌ Error updating patient: {str(e)}", exc_info=True)
            return Response(
                {
                    'error': str(e),
                    'detail': 'An error occurred while updating the patient'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def destroy(self, request, *args, **kwargs):
        """Override destroy to add better error handling"""
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
            
        except Exception as e:
            logger.error(f"❌ Error deleting patient: {str(e)}", exc_info=True)
            return Response(
                {
                    'error': str(e),
                    'detail': 'An error occurred while deleting the patient'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

def create_pdf_from_template(template_src, context_dict):
    """Renders a Django template to a PDF file."""
    html = render_to_string(template_src, context_dict)
    
    result = BytesIO()
    
    pdf = pisa.CreatePDF(
        html, 
        dest=result, 
        encoding='utf-8'
    )
    
    if not pdf.err:
        return result.getvalue()
    
    logger.error(f"Pisa PDF generation error: {pdf.err}")
    return None

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_patient_vr_form(request):
    """
    Saves Patient VR form data, generates the PDF using xhtml2pdf, 
    uploads to Azure Blob Storage with proper path structure, 
    emails the provider, and updates the patient's IVR PDF URL.
    """
    patient_id = request.data.get('patient_id') 
    form_data = request.data.get('form_data', {})

    if not patient_id:
        return Response(
            {"error": "Missing 'patient_id' in form submission body."},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # 1. Basic validation and patient lookup
        patient = Patient.objects.get(pk=patient_id, provider=request.user)
    except Patient.DoesNotExist:
        return Response(
            {"error": "Patient not found or does not belong to this provider."},
            status=status.HTTP_404_NOT_FOUND
        )
    
    try:
        # 2. PDF Generation (using a template)
        context = {
            'form_data': form_data,
            'patient': patient,
            'provider': request.user,
            'date_submitted': datetime.now().strftime("%B %d, %Y"),
            # Placeholder product lists for PDF rendering
            'PRODUCT_CHECKBOXES': [
                'Membrane Wrap Q4205', 'Activate Matrix Q4301', 'Restorgin Q4191', 'Amnio-Maxx Q4239',
                'Emerge Matrix Q4297', 'Helicoll Q4164', 'NeoStim TL Q4265', 'Derm-Maxx Q4238', 
                'AmnioAMP-MP Q4250', 'Membrane Wrap Hydro Q4290', 'Xcell Amnio Matrix Q4280', 
                'ACAp-atch Q4325', 'DermaBind FM Q4313', 'caregraFT Q4322', 'DermaBind TL Q4225', 
                'alloPLY Q4323', 'Revoshield+ Q4289',
            ],
            'POS_OPTIONS': ["Hospital Inpatient (21)", "Hospital Outpatient (22)", "Physician's Office (11)", "ASC (24)", "Home Health (12)"],
            'WOUND_BILLING_CODES': [
                {'label': 'Skin substitute procedure', 'code': '15271'},
                {'label': 'Wound care debridement (small)', 'code': '11042'},
                {'label': 'Wound care debridement (large)', 'code': '11045'},
            ]
        }

        pdf_bytes = create_pdf_from_template('patients/patient_ivr_form.html', context)

        if not pdf_bytes:
            raise Exception("Failed to generate PDF content.")

        # 3. Upload PDF to Azure Blob Storage with CORRECT path structure
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create proper path: patients_documents/provider_username/patient_name/pdf_name.pdf
        provider_slug = slugify(request.user.email.split('@')[0] if request.user.email else f"provider_{request.user.id}")
        patient_slug = slugify(patient.full_name or f"patient_{patient_id}")
        file_name = f"IVR_Form_{timestamp}.pdf"
        
        # ✅ CORRECTED PATH STRUCTURE
        blob_path = f"patients_documents/{provider_slug}/{patient_slug}/{file_name}"
        
        blob_service_client = BlobServiceClient.from_connection_string(
            settings.AZURE_STORAGE_CONNECTION_STRING
        )
        blob_client = blob_service_client.get_blob_client(
            container=settings.AZURE_MEDIA_CONTAINER, 
            blob=blob_path
        )
        
        blob_client.upload_blob(
            pdf_bytes, 
            overwrite=True, 
            content_settings=ContentSettings(content_type='application/pdf')
        )

        # Verify upload
        if not blob_client.exists():
            logger.error("Blob upload verification failed")
            raise Exception("Failed to verify file upload to Azure")

        # 4. Save to database
        provider_form = ProviderForm.objects.create(
            user=request.user,
            patient=patient,  
            form_type='Patient IVR Form',
            completed_form=blob_path,
            form_data=form_data, 
            completed=True
        )
        
        # 5. Generate SAS URL for response and email
        sas_url = generate_sas_url(blob_path, settings.AZURE_MEDIA_CONTAINER, 'r', 72)
        
        # 6. ✅ NEW: Send email to provider/user
        try:
            provider_email = request.user.email
            
            if provider_email:
                subject = f"IVR Form Submitted - {patient.full_name}"
                email_body = render_to_string('email/ivr_form_submission.html', {
                    'provider': request.user,
                    'patient': patient,
                    'form_data': form_data,
                    'sas_url': sas_url,
                    'submission_date': datetime.now().strftime('%B %d, %Y at %I:%M %p'),
                })
                
                email = EmailMessage(
                    subject, 
                    email_body, 
                    settings.DEFAULT_FROM_EMAIL, 
                    [provider_email]
                )
                email.content_subtype = "html"
                
                # Attach the PDF to the email
                email.attach(file_name, pdf_bytes, 'application/pdf')
                
                email.send()
                
                logger.info(f"✅ IVR Form email sent to: {provider_email}")
        except Exception as e:
            logger.warning(f"⚠️ Email failed for IVR form: {str(e)}")
        
        logger.info(f"✅ Patient IVR Form PDF submitted for Patient ID {patient_id}. Blob path: {blob_path}")

        return Response({
            "success": True,
            "form_id": provider_form.id,
            "sas_url": sas_url,
            "blob_path": blob_path,
            "message": "Patient IVR Form PDF saved, emailed, and linked successfully"
        }, status=201)
        
    except Exception as e:
        logger.error(f"Error saving Patient IVR form: {str(e)}", exc_info=True)
        return Response({
            "success": False,
            "error": "Failed to process Patient IVR form submission.",
            "detail": str(e)
        }, status=500)
        
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_patient_ivr_forms(request, patient_id):
    """
    Get all IVR forms for a specific patient.
    Only returns forms if the patient belongs to the requesting provider.
    """
    try:
        # Verify patient belongs to this provider
        try:
            patient = Patient.objects.get(pk=patient_id, provider=request.user)
        except Patient.DoesNotExist:
            return Response({
                "error": "Patient not found or does not belong to this provider."
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get all IVR forms for this specific patient
        ivr_forms = ProviderForm.objects.filter(
            user=request.user,
            patient=patient,
            form_type='Patient IVR Form',
            completed=True
        ).order_by('-date_created')
        
        forms_data = []
        
        for form in ivr_forms:
            # Generate SAS URL for the PDF
            pdf_url = None
            if form.completed_form:
                try:
                    pdf_url = generate_sas_url(
                        blob_name=form.completed_form,
                        container_name=settings.AZURE_MEDIA_CONTAINER,
                        permission='r',
                        expiry_hours=72
                    )
                except Exception as e:
                    logger.warning(f"Failed to generate SAS URL for form {form.id}: {str(e)}")
            
            # Build response data
            form_data = {
                'id': form.id,
                'patient_id': patient.id,
                'patient_name': patient.full_name,
                'patient_mrn': patient.medical_record_number,
                'ivr_status': patient.ivrStatus,
                'primary_insurance': patient.primary_insurance,
                'date_created': form.date_created.isoformat(),
                'pdf_url': pdf_url,
                'blob_path': form.completed_form,
                'form_data': form.form_data,
            }
            
            forms_data.append(form_data)
        
        logger.info(f"✅ Retrieved {len(forms_data)} IVR forms for patient {patient_id}")
        
        return Response(forms_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error fetching patient IVR forms: {str(e)}", exc_info=True)
        return Response({
            "success": False,
            "error": "Failed to retrieve IVR forms for patient",
            "detail": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)