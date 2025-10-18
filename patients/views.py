from rest_framework.permissions import IsAuthenticated
from patients import serializers as api_serializers
from rest_framework import generics, status
from rest_framework.response import Response
from .models import Patient
import logging

logger = logging.getLogger(__name__)
from provider_auth.models import User

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

    def create(self, request, *args, **kwargs):
        """Override create to add better error handling and logging"""
        logger.info("="*50)
        logger.info("🔍 PATIENT CREATION REQUEST")
        logger.info(f"User: {request.user.email} (ID: {request.user.id})")
        logger.info(f"Raw request data keys: {list(request.data.keys())}")
        logger.info("="*50)
        
        try:
            # Make a mutable copy of the data and remove provider fields
            data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
            
            # Remove any provider-related fields that shouldn't be in the request
            data.pop('provider', None)
            data.pop('provider_id', None)
            
            logger.info(f"Cleaned data keys: {list(data.keys())}")
            
            # Create serializer with cleaned data
            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            
            # Perform the create
            self.perform_create(serializer)
            
            headers = self.get_success_headers(serializer.data)
            logger.info(f"✅ Patient created successfully: {serializer.data.get('id')}")
            
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
            
        except Exception as e:
            logger.error(f"❌ Error creating patient: {str(e)}", exc_info=True)
            
            # Return a proper JSON error response instead of letting it become HTML
            return Response(
                {
                    'error': str(e),
                    'detail': 'An error occurred while creating the patient'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def perform_create(self, serializer):
        """Save the patient with the current user as the provider"""
        logger.info("="*50)
        logger.info("🔍 PERFORM CREATE")
        logger.info(f"User ID: {self.request.user.id}")
        logger.info(f"User Email: {self.request.user.email}")
        logger.info(f"User exists in DB: {User.objects.filter(id=self.request.user.id).exists()}")
        logger.info(f"Serializer validated_data keys: {list(serializer.validated_data.keys())}")
        logger.info(f"'provider' in validated_data: {'provider' in serializer.validated_data}")
        logger.info(f"'provider_id' in validated_data: {'provider_id' in serializer.validated_data}")
        logger.info("="*50)
        
        try:
            # Explicitly remove provider fields from validated_data just in case
            validated_data = serializer.validated_data
            validated_data.pop('provider', None)
            validated_data.pop('provider_id', None)
            
            # Save with the current user as provider
            patient = serializer.save(provider=self.request.user)
            logger.info(f"✅ Patient created successfully with ID: {patient.id}")
            logger.info(f"✅ Patient provider ID: {patient.provider_id}")
            
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
        """Override update to add better error handling"""
        try:
            # Remove provider fields from update data
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
            return Response(
                {
                    'error': str(e),
                    'detail': 'An error occurred while updating the patient'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def destroy(self, request, *args, **kwargs):
        """Override destroy to add better error handling"""
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
            
        except Exception as e:
            logger.error(f"❌ Error deleting patient: {str(e)}", exc_info=True)
            return Response(
                {
                    'error': str(e),
                    'detail': 'An error occurred while deleting the patient'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )