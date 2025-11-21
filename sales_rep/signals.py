# sales_rep/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_sales_rep_profile(sender, instance, created, **kwargs):
    """Auto-create SalesRep record when user has sales_rep role"""
    from sales_rep.models import SalesRep
    
    if instance.role == 'sales_rep':
        sales_rep, was_created = SalesRep.objects.get_or_create(
            user=instance,
            defaults={
                'name': instance.full_name or instance.get_full_name() or instance.username,
                'email': instance.email,
                'phone': str(instance.phone_number) if instance.phone_number else '',
            }
        )
        
        if was_created:
            logger.info(f"✅ SalesRep profile created for user: {instance.email}")
        else:
            # Optionally sync data if SalesRep already exists
            sales_rep.name = instance.full_name or instance.get_full_name() or sales_rep.name
            sales_rep.email = instance.email
            if instance.phone_number:
                sales_rep.phone = str(instance.phone_number)
            sales_rep.save()
            logger.info(f"✅ SalesRep profile updated for user: {instance.email}")