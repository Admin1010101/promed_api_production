from rest_framework import viewsets, permissions
from notes import serializers as api_serializers
from notes import models as api_models

class NotesView(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = api_models.Notes.objects.all()
    serializer_class = api_serializers.NotesSerializers
    
    def get_queryset(self):
        queryset = super().get_queryset()
        patient_id = self.request.query_params.get('patient')
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)
        return queryset
    
    
        
        
