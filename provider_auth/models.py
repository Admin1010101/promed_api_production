# provider_auth/models.py
from django.db import models
# NOTE: Import Group and Permission models for the custom M2M fields
from django.contrib.auth.models import AbstractUser, Group, Permission 
from django.db.models.signals import post_save
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _ # Required for Django field definitions
from sales_rep.models import SalesRep
from phonenumber_field.modelfields import PhoneNumberField
from promed_backend_api.storage_backends import AzureStaticStorage, AzureMediaStorage
import random
import uuid
# REMOVED: django.core.mail, django.template.loader (No longer needed here)

COUNTRY_CODE_CHOICES = (
    ('+1', 'United States'),
    ('+1', 'Canada'),
    ('+44', 'United Kingdom'),
    ('+33', 'France'),
    ('+39', 'Italy'),
    ('+49', 'Germany'),
    ('+34', 'Spain'),
)

verification_methods = (
    ('email', 'Email'),
    ('sms', 'SMS'),
)

USER_ROLES = (
    ('provider', 'Medical Provider'),
    ('sales_rep', 'Sales Representative'),
    ('admin', 'Administrator'),
    ('ceo', 'CEO'),
)

def generate_code():
    return str(random.randint(100000, 999999))

def user_directory_path(instance, filename):
    # file will be uploaded to: MEDIA_ROOT/user_<id>/<filename>
    return f'user_{instance.user.id}/{filename}'
#sends verify email from here
class User(AbstractUser):
    username = models.CharField(unique=True, max_length=255)
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255, null=True, blank=True)
    country_code = models.CharField(
        max_length=5,
        choices=COUNTRY_CODE_CHOICES,
        default='+1',
        help_text="Country dial code for reference (e.g. +1 for US)."
    )
    phone_number = PhoneNumberField(null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    facility = models.CharField(max_length=200, null=True, blank=True)
    facility_phone_number = models.CharField(max_length=20, null=True, blank=True)
    role = models.CharField(max_length=50, choices=USER_ROLES, default='provider')
    otp = models.CharField(max_length=100, null=True, blank=True)
    refresh_token = models.CharField(max_length=1000, null=True, blank=True)
    npi_number = models.CharField(max_length=10, null=True, blank=True)
    is_approved = models.BooleanField(default=False)
    welcome_email_sent = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    is_verified = models.BooleanField(default=False)

    # =========================================================
    # CRITICAL FIX: Explicitly define groups and user_permissions
    #               to resolve the SystemCheckError (fields.E304)
    # =========================================================
    groups = models.ManyToManyField(
        Group,
        verbose_name=_('groups'),
        blank=True,
        help_text=_('The groups this user belongs to. A user will get all permissions granted to each of their groups.'),
        related_name="provider_auth_users", # <-- UNIQUE RELATED NAME
        related_query_name="provider_auth_user",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name="provider_auth_permissions", # <-- UNIQUE RELATED NAME
        related_query_name="provider_auth_permission",
    )
    # =========================================================

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self) -> str:
        return f'{self.email} | {self.date_joined}'

    def save(self, *args, **kwargs):
        if not self.username:
            self.username = self.email.split('@')[0] if '@' in self.email else self.email
        if not self.full_name:
            self.full_name = f"{self.first_name} {self.last_name}".strip() or self.username
        super().save(*args, **kwargs)

class Profile(models.Model):
    # ... (Profile model content remains the same)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    sales_rep = models.ForeignKey(SalesRep, on_delete=models.SET_NULL, null=True, blank=True, related_name="providers")
    image = models.FileField(
        storage= AzureMediaStorage, 
        upload_to=user_directory_path,
        default='defaults/default_user.jpg', 
        null=True,
        blank=True
    )

    full_name = models.CharField(max_length=255, null=True, blank=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=255, null=True, blank=True)
    bio = models.TextField(blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.full_name or self.user.username)

    def save(self, *args, **kwargs):
        if not self.full_name:
            self.full_name = self.user.username
        super().save(*args, **kwargs)


class Verification_Code(models.Model):
    # ... (Verification_Code model content remains the same)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    method = models.CharField(max_length=10, choices=verification_methods)
    created_at = models.DateTimeField(default=timezone.now)
    session_id = models.CharField(max_length=100, null=True, blank=True)

    def is_expired(self):
        return timezone.now() > self.created_at + timezone.timedelta(minutes=10)
        
class EmailVerificationToken(models.Model):
    # ... (EmailVerificationToken model content remains the same)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Token for {self.user.email}"

class PasswordResetToken(models.Model):
    # ... (PasswordResetToken model content remains the same)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() > self.created_at + timezone.timedelta(minutes=30)
    
