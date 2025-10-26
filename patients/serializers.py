# patients/serializers.py
from rest_framework import serializers
from patients.models import Patient, IVRForm
from onboarding_ops.models import ProviderForm
from django.conf import settings
from django.utils import timezone
from utils.azure_storage import generate_sas_url
import logging


logger = logging.getLogger(__name__)


class PatientSerializer(serializers.ModelSerializer):
    """Serializer for Patient model with IVR-related computed fields"""
    # IVR-related computed fields - no source needed since they match property names
    latest_ivr_status = serializers.CharField(read_only=True)
    latest_ivr_status_display = serializers.CharField(read_only=True)
    latest_ivr_pdf_url = serializers.CharField(read_only=True)
    ivr_count = serializers.IntegerField(read_only=True)
    has_approved_ivr = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Patient
        fields = [
            'id',
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
            'created_at',  # ✅ FIXED: changed from date_created
            'updated_at',  # ✅ FIXED: changed from date_updated
            'activate_Account',
            # IVR-related fields
            'latest_ivr_status',
            'latest_ivr_status_display',
            'latest_ivr_pdf_url',
            'ivr_count',
            'has_approved_ivr',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']  # ✅ FIXED: changed field names


class IVRFormSerializer(serializers.ModelSerializer):
    """Full serializer for IVR forms with all details"""
    provider_name = serializers.SerializerMethodField()
    patient_name = serializers.SerializerMethodField()
    reviewed_by_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = IVRForm
        fields = [
            'id',
            'provider',
            'provider_name',
            'patient',
            'patient_name',
            'physician_name',
            'contact_name',
            'phone',
            'facility_address',
            'facility_city_state_zip',
            'wound_size_length',
            'wound_size_width',
            'pdf_url',
            'pdf_blob_name',
            'status',
            'status_display',
            'admin_notes',
            'submitted_at',
            'updated_at',
            'reviewed_at',
            'reviewed_by',
            'reviewed_by_name',
        ]
        read_only_fields = [
            'id',
            'provider',
            'submitted_at',
            'updated_at',
            'reviewed_at',
            'reviewed_by',
        ]
    
    def get_provider_name(self, obj):
        """Safely get provider name"""
        if hasattr(obj.provider, 'full_name'):
            return obj.provider.full_name
        return f"{obj.provider.first_name} {obj.provider.last_name}" if hasattr(obj.provider, 'first_name') else obj.provider.email
    
    def get_patient_name(self, obj):
        """Safely get patient name"""
        return f"{obj.patient.first_name} {obj.patient.last_name}"
    
    def get_reviewed_by_name(self, obj):
        """Safely get reviewed_by name"""
        if not obj.reviewed_by:
            return None
        if hasattr(obj.reviewed_by, 'full_name'):
            return obj.reviewed_by.full_name
        return f"{obj.reviewed_by.first_name} {obj.reviewed_by.last_name}" if hasattr(obj.reviewed_by, 'first_name') else obj.reviewed_by.email


class IVRFormCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new IVR forms"""
    class Meta:
        model = IVRForm
        fields = [
            'patient',
            'physician_name',
            'contact_name',
            'phone',
            'facility_address',
            'facility_city_state_zip',
            'wound_size_length',
            'wound_size_width',
            'pdf_url',
            'pdf_blob_name',
        ]
    
    def create(self, validated_data):
        # Provider is set from the request user in the view
        validated_data['provider'] = self.context['request'].user
        return super().create(validated_data)


class IVRFormListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing IVR forms"""
    patient_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    reviewed_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = IVRForm
        fields = [
            'id',
            'patient',
            'patient_name',
            'physician_name',
            'contact_name',
            'phone',
            'status',
            'status_display',
            'submitted_at',
            'reviewed_at',
            'reviewed_by',
            'reviewed_by_name',
            'admin_notes',
            'pdf_url',
        ]
    
    def get_patient_name(self, obj):
        return f"{obj.patient.first_name} {obj.patient.last_name}"
    
    def get_reviewed_by_name(self, obj):
        """Safely get reviewed_by name"""
        if not obj.reviewed_by:
            return None
        if hasattr(obj.reviewed_by, 'full_name'):
            return obj.reviewed_by.full_name
        return f"{obj.reviewed_by.first_name} {obj.reviewed_by.last_name}" if hasattr(obj.reviewed_by, 'first_name') else obj.reviewed_by.email


class IVRFormUpdateStatusSerializer(serializers.ModelSerializer):
    """Serializer for admin to update IVR status"""
    class Meta:
        model = IVRForm
        fields = ['status', 'admin_notes']
    
    def validate_status(self, value):
        valid_statuses = ['pending', 'approved', 'denied', 'cancelled']
        if value not in valid_statuses:
            raise serializers.ValidationError(
                f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )
        return value
    
    def update(self, instance, validated_data):
        status = validated_data.get('status')
        admin_notes = validated_data.get('admin_notes', '')
        
        request = self.context.get('request')
        reviewed_by = request.user if request else None
        
        if status == 'approved':
            instance.mark_as_approved(reviewed_by_user=reviewed_by, notes=admin_notes)
        elif status == 'denied':
            instance.mark_as_denied(reviewed_by_user=reviewed_by, notes=admin_notes)
        elif status == 'cancelled':
            instance.status = 'cancelled'
            instance.reviewed_at = timezone.now()
            if admin_notes:
                instance.admin_notes = admin_notes
            instance.save()
        else:
            instance.status = status
            if admin_notes:
                instance.admin_notes = admin_notes
            instance.save()
        
        return instance