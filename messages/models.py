from django.db import models
from django.conf import settings
from sales_rep.models import SalesRep

class Message(models.Model):
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")
    recipient = models.ForeignKey(SalesRep, on_delete=models.CASCADE, related_name="received_messages")
    subject = models.CharField(max_length=255, null=True, blank=True)
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"From {self.sender.email} to {self.recipient.name}"

