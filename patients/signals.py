from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Patient
from notifications.models import Notification


@receiver(post_save, sender=Patient)
def create_patient_notification(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(
            recipient = instance.provider,
            type = 'new_patient',
            message = f'New Patient added: {instance.full_name}'
        )
        