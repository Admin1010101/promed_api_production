# patients/serializers.py
from rest_framework import serializers
from .models import Patient

class PatientSerializer(serializers.ModelSerializer):
    provider = serializers.PrimaryKeyRelatedField(read_only=True)
    full_name = serializers.CharField(read_only=True)  # Add this for the property
    
    class Meta:
        model = Patient
        fields = '__all__'
        read_only_fields = ['provider', 'date_created', 'date_updated']
        

