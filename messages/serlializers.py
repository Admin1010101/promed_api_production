from rest_framework import serializers
from .models import Message

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['id', 'subject', 'body', 'timestamp', 'is_read']
        read_only_fields = ['id', 'timestamp', 'is_read']

    def create(self, validated_data):
        user = self.context['request'].user
        sales_rep = getattr(user.profile, 'sales_rep', None)
        if not sales_rep:
            raise serializers.ValidationError('No sales rep assigned to this provider.')
        
        return Message.objects.create(
            sender=user,
            recipient=sales_rep,
            **validated_data
        )
