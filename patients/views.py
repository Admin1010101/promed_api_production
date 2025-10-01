from rest_framework.permissions import IsAuthenticated
from patients import serializers as api_serializers
from rest_framework import generics, status
from .models import Patient
class PatientListView(generics.ListCreateAPIView):
    serializer_class = api_serializers.PatientSerializer
    permission_classes = [IsAuthenticated]

    # Get the list of patients for the authenticated provider
    def get_queryset(self):
        return Patient.objects.filter(provider=self.request.user)
    
    # Set the provider to the authenticated user
    def perform_create(self, serializer):
        serializer.save(provider=self.request.user)
        
class PatientDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = api_serializers.PatientSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Patient.objects.filter(provider=self.request.user)
