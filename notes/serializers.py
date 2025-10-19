from rest_framework import serializers
from notes import models as api_models

class NotesSerializers(serializers.ModelSerializer):
    class Meta:
        model = api_models.Notes
        fields = '__all__'
    
    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError("Title cannot be empty")
        return value.strip()
    
    def validate_body(self, value):
        if not value.strip():
            raise serializers.ValidationError("Note content cannot be empty")
        return value