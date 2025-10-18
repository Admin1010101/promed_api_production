from rest_framework.permissions import IsAuthenticated
from patients import serializers as api_serializers
from rest_framework import generics, status
from rest_framework.response import Response
from .models import Patient
import logging

logger = logging.getLogger(__name__)

from provider_auth.models import User  # Add this import at the top

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
    
    def perform_create(self, serializer):
        logger.info("="*50)
        logger.info("🔍 PATIENT CREATION DEBUG")
        logger.info(f"User ID: {self.request.user.id}")
        logger.info(f"User Email: {self.request.user.email}")
        logger.info(f"User exists in DB: {User.objects.filter(id=self.request.user.id).exists()}")
        logger.info(f"Raw request data: {self.request.data}")
        logger.info(f"Serializer validated_data: {serializer.validated_data}")
        logger.info(f"'provider' in validated_data: {'provider' in serializer.validated_data}")
        logger.info(f"'provider_id' in validated_data: {'provider_id' in serializer.validated_data}")
        logger.info("="*50)
        
        try:
            patient = serializer.save(provider=self.request.user)
            logger.info(f"✅ Patient created successfully with ID: {patient.id}")
        except Exception as e:
            logger.error(f"❌ Error creating patient: {e}", exc_info=True)
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