from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Order
from notifications.models import Notification

@receiver(post_save, sender=Order)
def create_order_notification(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(
            recipient=instance.provider,
            type='new_order',
            message=f"New order placed for patient: {instance.patient.full_name}"
        )

        
