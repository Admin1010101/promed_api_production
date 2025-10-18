# patients/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Patient
from notifications.models import Notification
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Patient)
def create_patient_notification(sender, instance, created, **kwargs):
    """Create a notification when a new patient is added"""
    if created:
        # ✅ Add validation and error handling
        if not instance.provider:
            logger.warning(f"Patient {instance.id} created without a provider - skipping notification")
            return
        
        try:
            logger.info(f"Creating notification for provider {instance.provider.id} ({instance.provider.email})")
            
            Notification.objects.create(
                recipient=instance.provider,
                type='new_patient',
                message=f'New Patient added: {instance.full_name}'
            )
            
            logger.info(f"✅ Notification created successfully for patient {instance.id}")
            
        except Exception as e:
            # Don't let notification failure break patient creation
            logger.error(f"❌ Failed to create notification for patient {instance.id}: {str(e)}", exc_info=True)