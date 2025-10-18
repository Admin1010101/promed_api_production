# patients/serializers.py
from rest_framework import serializers
from .models import Patient

class PatientSerializer(serializers.ModelSerializer):
    provider = serializers.PrimaryKeyRelatedField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    
    class Meta:
        model = Patient
        fields = '__all__'
        read_only_fields = ['id', 'provider', 'date_created', 'date_updated', 'full_name']
        
    def validate(self, data):
        """Extra safety: Remove provider fields if they somehow get through"""
        data.pop('provider', None)
        data.pop('provider_id', None)
        return data
    
    def to_internal_value(self, data):
        """Remove provider fields before validation"""
        if isinstance(data, dict):
            data = data.copy()
            data.pop('provider', None)
            data.pop('provider_id', None)
        return super().to_internal_value(data)
