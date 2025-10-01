from django.shortcuts import render
from rest_framework import permissions, generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
import notifications.serializers as api_serializers
import notifications.models as api_models
from provider_auth.models import User
from django.utils import timezone
from django.db import models
        
class NotificationListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = api_serializers.NotificationSerializer
    
    def get_queryset(self):
        return api_models.Notification.objects.filter(
        recipient=self.request.user,
    ).filter(
        models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=timezone.now())
    )
    
class MarkNotificationReadView(generics.UpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = api_models.Notification.objects.all()
    serializer_class = api_serializers.NotificationSerializer  # Assuming it includes `is_read` field

    def update(self, request, *args, **kwargs):
        notification = self.get_object()
        if notification.recipient != request.user:
            raise PermissionDenied("You do not have permission to mark this notification.")

        notification.is_read = True
        notification.save()
        return Response({'status': 'marked as read'}, status=status.HTTP_200_OK)
    
class UnreadNotificationCountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        count = api_models.Notification.objects.filter(recipient=request.user, is_read=False).count()
        return Response({'unread_count': count})
    
class NotificationDeleteView(generics.DestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = api_models.Notification.objects.all()

    def perform_destroy(self, instance):
        if instance.recipient != self.request.user:
            raise PermissionDenied("You do not have permission to delete this notification.")
        instance.delete()

class BroadcastNotificationView(APIView):
    permission_classes = [permissions.IsAdminUser]  # Only admins or authorized users

    def post(self, request):
        message = request.data.get('message')
        notif_type = request.data.get('type', 'announcement')

        if not message:
            return Response({'error': 'Message field is required.'}, status=status.HTTP_400_BAD_REQUEST)

        all_users = User.objects.all()

        notifications = [
            api_models.Notification(
                recipient=user,
                message=message,
                type=notif_type,
                broadcast=True
            )
            for user in all_users
        ]

        api_models.Notification.objects.bulk_create(notifications)

        return Response({'detail': f'Notification sent to {len(notifications)} users.'}, status=status.HTTP_201_CREATED)

