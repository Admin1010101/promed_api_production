# patients/serializers.py
from rest_framework import serializers
from patients.models import Patient
from onboarding_ops.models import ProviderForm
from django.conf import settings
from utils.azure_storage import generate_sas_url
import logging

logger = logging.getLogger(__name__)

class PatientSerializer(serializers.ModelSerializer):
    """
    Serializer for Patient model with computed IVR PDF URL.
    """
    latestIvrPdfUrl = serializers.SerializerMethodField()
    
    class Meta:
        model = Patient
        fields = [
            'id',
            'provider',
            'first_name',
            'last_name',
            'middle_initial',
            'date_of_birth',
            'email',
            'address',
            'city',
            'state',
            'zip_code',
            'phone_number',
            'primary_insurance',
            'primary_insurance_number',
            'secondary_insurance',
            'secondary_insurance_number',
            'tertiary_insurance',
            'tertiary_insurance_number',
            'medical_record_number',
            'wound_size_length',
            'wound_size_width',
            'ivrStatus',
            'activate_Account',
            'date_created',
            'date_updated',
            'latestIvrPdfUrl',  # Computed field
        ]
        read_only_fields = ['id', 'provider', 'date_created', 'date_updated', 'latestIvrPdfUrl']
    
    def get_latestIvrPdfUrl(self, obj):
        """
        Get the latest IVR form PDF URL with SAS token for the patient.
        Returns None if no IVR form exists.
        """
        try:
            # Get the most recent IVR form for this patient
            latest_ivr = ProviderForm.objects.filter(
                patient=obj,
                form_type='Patient IVR Form',
                completed=True
            ).order_by('-date_created').first()
            
            if latest_ivr and latest_ivr.completed_form:
                # Generate SAS URL with 72 hour expiry
                sas_url = generate_sas_url(
                    blob_name=latest_ivr.completed_form,
                    container_name=settings.AZURE_MEDIA_CONTAINER,
                    permission='r',
                    expiry_hours=72
                )
                return sas_url
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating IVR PDF URL for patient {obj.id}: {str(e)}")
            return None
