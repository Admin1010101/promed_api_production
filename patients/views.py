from rest_framework.permissions import IsAuthenticated
from patients import serializers as api_serializers
from rest_framework import generics, status
from .models import Patient

# FIX: Add imports for the check (though usually unnecessary if permissions are set)
from django.contrib.auth.models import AnonymousUser 
from django.db.models.query import QuerySet # Added for type hinting if needed

class PatientListView(generics.ListCreateAPIView):
    serializer_class = api_serializers.PatientSerializer
    permission_classes = [IsAuthenticated]

    # FIX APPLIED HERE
    def get_queryset(self):
        # 1. Bypass schema generation (common drf-yasg/spectacular fix)
        if getattr(self, 'swagger_fake_view', False):
            return Patient.objects.none()

        # 2. Safety check: ensure user is authenticated before filtering
        # Since permission_classes includes IsAuthenticated, this should always be True for live traffic,
        # but it prevents issues if permissions are bypassed or overridden.
        if self.request.user.is_authenticated:
            return Patient.objects.filter(provider=self.request.user)
        
        # Fallback for unauthenticated access (shouldn't happen with IsAuthenticated, but safe)
        return Patient.objects.none()
    
    # Set the provider to the authenticated user
    def perform_create(self, serializer):
        serializer.save(provider=self.request.user)
        
class PatientDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = api_serializers.PatientSerializer
    permission_classes = [IsAuthenticated]

    # FIX APPLIED HERE
    def get_queryset(self):
        # 1. Bypass schema generation (common drf-yasg/spectacular fix)
        if getattr(self, 'swagger_fake_view', False):
            return Patient.objects.none()

        # 2. Safety check: ensure user is authenticated before filtering
        if self.request.user.is_authenticated:
            return Patient.objects.filter(provider=self.request.user)

        return Patient.objects.none()