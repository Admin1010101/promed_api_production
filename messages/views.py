# messages/views.py
from rest_framework import generics, permissions
from .models import Message
from .serlializers import MessageSerializer

class MessageListCreateView(generics.ListCreateAPIView):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Message.objects.filter(sender=self.request.user)

class MessageDetailView(generics.RetrieveUpdateAPIView):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

