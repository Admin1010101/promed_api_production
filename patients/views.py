from rest_framework.permissions import IsAuthenticated
from patients import serializers as api_serializers
from rest_framework import generics, status
from rest_framework.response import Response
from .models import Patient
import logging

logger = logging.getLogger(__name__)

class PatientListView(generics.ListCreateAPIView):
    serializer_class = api_serializers.PatientSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Bypass schema generation
        if getattr(self, 'swagger_fake_view', False):
            return Patient.objects.none()
        
        # Log for debugging
        logger.info(f"PatientListView - User: {self.request.user.email if hasattr(self.request.user, 'email') else self.request.user}")
        logger.info(f"PatientListView - User ID: {self.request.user.id}")
        logger.info(f"PatientListView - Authenticated: {self.request.user.is_authenticated}")
        
        if self.request.user.is_authenticated:
            queryset = Patient.objects.filter(provider=self.request.user)
            logger.info(f"PatientListView - Found {queryset.count()} patients")
            return queryset
        
        logger.warning("PatientListView - Unauthenticated request")
        return Patient.objects.none()
    
    def list(self, request, *args, **kwargs):
        """Override to add logging"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        logger.info(f"PatientListView - Returning {len(serializer.data)} patients")
        return Response(serializer.data)
    
    def perform_create(self, serializer):
        logger.info(f"Creating patient for user {self.request.user.id}")
        serializer.save(provider=self.request.user)

class PatientDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = api_serializers.PatientSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Patient.objects.none()
        
        if self.request.user.is_authenticated:
            return Patient.objects.filter(provider=self.request.user)
        
        return Patient.objects.none()