from rest_framework import serializers
from .models import Patient
class PatientSerializer(serializers.ModelSerializer):
    provider = serializers.PrimaryKeyRelatedField(read_only=True)  # Can be replaced with a nested serializer
    class Meta:
        model = Patient
        fields = '__all__'
        

