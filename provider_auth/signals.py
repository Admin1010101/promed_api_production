# signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

from .models import User

# provider_auth/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import User
from datetime import datetime

@receiver(post_save, sender=User)
def send_welcome_email_on_approval(sender, instance, created, **kwargs):
    if not created and instance.is_verified and instance.is_approved and not instance.welcome_email_sent:
        # Send the welcome email
        html_message = render_to_string('provider_auth/welcome_email.html', {
            'user': instance,
            'year': datetime.now().year,
        })

        send_mail(
            subject='Welcome to ProMed Health Plus!',
            message='You have been approved. You may now log in.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[instance.email],
            html_message=html_message,
            fail_silently=False
        )

        # Update user so the email isn’t sent again
        instance.welcome_email_sent = True
        instance.save(update_fields=['welcome_email_sent'])

