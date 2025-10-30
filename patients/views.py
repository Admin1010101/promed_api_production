# patients/views.py (REWRITTEN AND FIXED)
import logging
from datetime import datetime
from django.conf import settings
from django.utils.text import slugify
from django.template.loader import render_to_string 
from django.shortcuts import get_object_or_404
from django.core.mail import EmailMessage
from django.db.models import Count, Q
from io import BytesIO 

# Import pisa for PDF generation
from xhtml2pdf import pisa 

from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from . import serializers as api_serializers

from azure.storage.blob import BlobServiceClient
from azure.storage.blob import ContentSettings 

from patients.models import Patient, IVRForm
# ❌ Removed redundant ProviderForm import if it's not used elsewhere in this file
# from onboarding_ops.models import ProviderForm 
from utils.azure_storage import generate_sas_url 
from provider_auth.models import User

logger = logging.getLogger(__name__)

# --- PDF Helper Function (Unchanged) ---

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

# --- Patient Views (Unchanged) ---

class PatientListView(generics.ListCreateAPIView):
    serializer_class = api_serializers.PatientSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Patient.objects.none()
        
        if self.request.user.is_authenticated:
            return Patient.objects.filter(provider=self.request.user)
        
        return Patient.objects.none()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        logger.info("🔍 PATIENT CREATION REQUEST")
        try:
            data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
            data.pop('provider', None)
            data.pop('provider_id', None)
            
            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            
            headers = self.get_success_headers(serializer.data)
            logger.info(f"✅ Patient created successfully: {serializer.data.get('id')}")
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
            
        except Exception as e:
            logger.error(f"❌ Error creating patient: {str(e)}", exc_info=True)
            return Response({'error': str(e), 'detail': 'An error occurred while creating the patient'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def perform_create(self, serializer):
        try:
            validated_data = serializer.validated_data
            validated_data.pop('provider', None)
            validated_data.pop('provider_id', None)
            patient = serializer.save(provider=self.request.user)
            logger.info(f"✅ Patient created with ID: {patient.id}")
            
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
        try:
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
            return Response({'error': str(e), 'detail': 'An error occurred while updating the patient'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
            
        except Exception as e:
            logger.error(f"❌ Error deleting patient: {str(e)}", exc_info=True)
            return Response({'error': str(e), 'detail': 'An error occurred while deleting the patient'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# --- IVR Submission Function (FIXED to use IVRForm model) ---
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_patient_vr_form(request):
    """
    Saves Patient VR form data, generates the PDF, uploads to Azure, 
    emails the provider, and creates a record in the IVRForm model.
    """
    patient_id = request.data.get('patient_id') 
    form_data = request.data.get('form_data', {})

    if not patient_id:
        return Response({"error": "Missing 'patient_id' in form submission body."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # 1. Basic validation and patient lookup
        patient = Patient.objects.get(pk=patient_id, provider=request.user)
    except Patient.DoesNotExist:
        return Response({"error": "Patient not found or does not belong to this provider."}, status=status.HTTP_404_NOT_FOUND)
    
    try:
        # 2. PDF Generation (Context includes depth for documentation)
        context = {
            'form_data': form_data,
            'patient': patient,
            'provider': request.user,
            'date_submitted': datetime.now().strftime("%B %d, %Y"),
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

        # 3. Upload PDF to Azure Blob Storage
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        provider_slug = slugify(request.user.email.split('@')[0] if request.user.email else f"provider_{request.user.id}")
        patient_slug = slugify(patient.full_name or f"patient_{patient_id}")
        file_name = f"IVR_Form_{timestamp}.pdf"
        blob_path = f"patients_documents/{provider_slug}/{patient_slug}/{file_name}"
        
        blob_service_client = BlobServiceClient.from_connection_string(settings.AZURE_STORAGE_CONNECTION_STRING)
        blob_client = blob_service_client.get_blob_client(container=settings.AZURE_MEDIA_CONTAINER, blob=blob_path)
        
        blob_client.upload_blob(pdf_bytes, overwrite=True, content_settings=ContentSettings(content_type='application/pdf'))

        if not blob_client.exists():
            logger.error("Blob upload verification failed")
            raise Exception("Failed to verify file upload to Azure")

        # 4. Save to IVRForm model with all wound measurements
        ivr_form = IVRForm.objects.create(
            provider=request.user,
            patient=patient,  
            status='pending',
            pdf_blob_name=blob_path,
            # Map fields from form_data to IVRForm's fields
            physician_name=form_data.get('physician_name', patient.full_name),
            contact_name=form_data.get('contact_name', patient.full_name),
            phone=form_data.get('phone', patient.phone_number),
            facility_address=form_data.get('facility_address', patient.address),
            facility_city_state_zip=form_data.get('facility_city_state_zip', f"{patient.city}, {patient.state} {patient.zip_code}"),
            # ✅ Include all wound measurements (depth is for documentation, not ordering)
            wound_size_length=form_data.get('wound_size_length', patient.wound_size_length),
            wound_size_width=form_data.get('wound_size_width', patient.wound_size_width),
            wound_size_depth=form_data.get('wound_size_depth', patient.wound_size_depth),
        )
        
        # 5. Generate SAS URL for response and email
        sas_url = generate_sas_url(blob_path, settings.AZURE_MEDIA_CONTAINER, 'r', 72)
        
        # Optional: Update the IVRForm object with the public URL if the model has a pdf_url field
        if hasattr(ivr_form, 'pdf_url'):
             ivr_form.pdf_url = sas_url
             ivr_form.save()

        # 6. Send email to provider/user
        try:
            provider_email = request.user.email
            if provider_email:
                # Calculate surface area for email (used for ordering calculations)
                wound_surface_area = 0
                if patient.wound_size_length and patient.wound_size_width:
                    wound_surface_area = float(patient.wound_size_length) * float(patient.wound_size_width)
                
                subject = f"IVR Form Submitted - {patient.full_name}"
                email_body = render_to_string('email/ivr_form_submission.html', {
                    'provider': request.user,
                    'patient': patient,
                    'form_data': form_data,
                    'sas_url': sas_url,
                    'submission_date': datetime.now().strftime('%B %d, %Y at %I:%M %p'),
                    'wound_surface_area': round(wound_surface_area, 2),
                    'max_order_area': round(wound_surface_area * 1.2, 2),
                })
                email = EmailMessage(subject, email_body, settings.DEFAULT_FROM_EMAIL, [provider_email])
                email.content_subtype = "html"
                email.attach(file_name, pdf_bytes, 'application/pdf')
                email.send()
                logger.info(f"✅ IVR Form email sent to: {provider_email}")
        except Exception as e:
            logger.warning(f"⚠️ Email failed for IVR form: {str(e)}")
        
        logger.info(f"✅ Patient IVR Form PDF submitted for Patient ID {patient_id}. Blob path: {blob_path}")

        return Response({
            "success": True,
            "form_id": ivr_form.id,
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

class IVRFormListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return api_serializers.IVRFormCreateSerializer
        return api_serializers.IVRFormListSerializer
    
    def get_queryset(self):
        return IVRForm.objects.filter(
            provider=self.request.user
        ).select_related('patient', 'provider').order_by('-submitted_at')
    
    def perform_create(self, serializer):
        serializer.save(provider=self.request.user)


class IVRFormDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = api_serializers.IVRFormSerializer
    
    def get_queryset(self):
        return IVRForm.objects.filter(provider=self.request.user)


class PatientIVRFormsView(generics.ListAPIView):
    """
    FIXED: This is the definitive endpoint for listing a patient's IVR forms.
    It correctly uses the IVRForm model and serializer.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = api_serializers.IVRFormListSerializer
    
    def get_queryset(self):
        patient_id = self.kwargs.get('patient_id')
        return IVRForm.objects.filter(
            patient_id=patient_id,
            provider=self.request.user
        ).select_related('patient', 'provider').order_by('-submitted_at')


class IVRFormWithdrawView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, pk):
        try:
            ivr_form = get_object_or_404(IVRForm, pk=pk, provider=request.user)
            if ivr_form.withdraw():
                return Response({'message': 'IVR form withdrawn successfully'}, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'Only pending IVR forms can be withdrawn'}, status=status.HTTP_400_BAD_REQUEST)
        except IVRForm.DoesNotExist:
            return Response({'error': 'IVR form not found'}, status=status.HTTP_404_NOT_FOUND)


# ============ ADMIN IVR VIEWS (Unchanged) ============

class AdminIVRFormListView(generics.ListAPIView):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = api_serializers.IVRFormSerializer
    
    def get_queryset(self):
        queryset = IVRForm.objects.all().select_related('patient', 'provider', 'reviewed_by').order_by('-submitted_at')
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        patient_id = self.request.query_params.get('patient')
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)
        provider_id = self.request.query_params.get('provider')
        if provider_id:
            queryset = queryset.filter(provider_id=provider_id)
        return queryset


class AdminIVRFormDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAdminUser]
    queryset = IVRForm.objects.all()
    
    def get_serializer_class(self):
        if self.request.method in ['PATCH', 'PUT']:
            return api_serializers.IVRFormUpdateStatusSerializer
        return api_serializers.IVRFormSerializer
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, 
            data=request.data, 
            partial=partial,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return_serializer = api_serializers.IVRFormSerializer(instance)
        return Response(return_serializer.data)


class AdminIVRStatsView(APIView):
    permission_classes = [permissions.IsAdminUser]
    
    def get(self, request):
        stats =  IVRForm.objects.aggregate(
            total=Count('id'),
            pending=Count('id', filter=Q(status='pending')),
            approved=Count('id', filter=Q(status='approved')),
            denied=Count('id', filter=Q(status='denied')),
            cancelled=Count('id', filter=Q(status='cancelled')),
            withdrawn=Count('id', filter=Q(status='withdrawn')),
        )
        
        return Response(stats, status=status.HTTP_200_OK)
    