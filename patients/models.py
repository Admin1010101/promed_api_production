# patients/models.py - UPDATED to include wound_size_depth

from django.db import models
from django.conf import settings
from phonenumber_field.modelfields import PhoneNumberField
from provider_auth.models import User
from django.utils import timezone

ivr_status_choices = (("Pending", "Pending"), ("Approved", "Approved"), ("Denied", "Denied"))
account_activation_choices = (("Activated", "Activated"), ("Deactivated", "Deactivated"))

class IVRForm(models.Model):
    """
    Individual Verification Requirements (IVR) forms.
    Each patient can have multiple IVR submissions, each with its own approval status.
    """
    
    IVR_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
        ('cancelled', 'Cancelled'),
        ('withdrawn', 'Withdrawn by Provider'),
    ]
    
    # Relationships
    provider = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='ivr_forms',
        help_text="The provider who submitted this IVR form"
    )
    patient = models.ForeignKey(
        'Patient',
        on_delete=models.CASCADE, 
        related_name='ivr_forms',
        help_text="The patient this IVR form is for"
    )
    
    # IVR Form Data fields
    physician_name = models.CharField(max_length=255, blank=True)
    contact_name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    facility_address = models.TextField(blank=True)
    facility_city_state_zip = models.CharField(max_length=255, blank=True)
    
    # ✅ UPDATED: Wound information - Added depth field
    wound_size_length = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Wound length in cm (head to toe)"
    )
    wound_size_width = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Wound width in cm (side to side, perpendicular to length)"
    )
    wound_size_depth = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Wound depth in cm (measured at deepest point)"
    )
    
    # PDF Storage
    pdf_url = models.URLField(
        max_length=500, 
        blank=True,
        help_text="Azure Blob Storage URL for the generated PDF"
    )
    pdf_blob_name = models.CharField(
        max_length=255, 
        blank=True,
        help_text="Blob name in Azure Storage"
    )
    
    # Status and Tracking
    status = models.CharField(
        max_length=20,
        choices=IVR_STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    
    admin_notes = models.TextField(
        blank=True,
        help_text="Internal notes about approval/denial decision"
    )
    
    # Timestamps
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_ivr_forms'
    )
    
    class Meta:
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['patient', '-submitted_at']),
            models.Index(fields=['provider', '-submitted_at']),
            models.Index(fields=['status', '-submitted_at']),
        ]
        verbose_name = 'IVR Form'
        verbose_name_plural = 'IVR Forms'
    
    def __str__(self):
        return f"IVR-{self.id} | {self.patient.first_name} {self.patient.last_name} | {self.get_status_display()}"
    
    def mark_as_approved(self, reviewed_by_user=None, notes=""):
        self.status = 'approved'
        self.reviewed_at = timezone.now()
        self.reviewed_by = reviewed_by_user
        if notes:
            self.admin_notes = notes
        self.save(update_fields=['status', 'reviewed_at', 'reviewed_by', 'admin_notes', 'updated_at'])
    
    def mark_as_denied(self, reviewed_by_user=None, notes=""):
        self.status = 'denied'
        self.reviewed_at = timezone.now()
        self.reviewed_by = reviewed_by_user
        if notes:
            self.admin_notes = notes
        self.save(update_fields=['status', 'reviewed_at', 'reviewed_by', 'admin_notes', 'updated_at'])
    
    def withdraw(self):
        """Allow provider to withdraw their pending IVR submission"""
        if self.status == 'pending':
            self.status = 'withdrawn'
            self.save(update_fields=['status', 'updated_at'])
            return True
        return False
    
    @property
    def is_approved(self):
        return self.status == 'approved'


class Patient(models.Model):
    provider = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='patients')
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    middle_initial = models.CharField(max_length=1, null=True, blank=True)
    date_of_birth = models.DateField(blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=255, null=True, blank=True)
    state = models.CharField(max_length=255, null=True, blank=True)
    zip_code = models.CharField(max_length=20, null=True, blank=True)
    phone_number = PhoneNumberField(max_length=20, null=True, blank=True)
    primary_insurance = models.CharField(max_length=255, null=True, blank=True)
    primary_insurance_number = models.CharField(max_length=50, null=True, blank=True)
    secondary_insurance = models.CharField(max_length=255, null=True, blank=True)
    secondary_insurance_number = models.CharField(max_length=50, null=True, blank=True)
    tertiary_insurance = models.CharField(max_length=255, null=True, blank=True)
    tertiary_insurance_number = models.CharField(max_length=255, null=True, blank=True)
    medical_record_number = models.CharField(max_length=255, null=True, blank=True)
    
    # ✅ UPDATED: Wound measurements - Added depth field
    wound_size_length = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Wound length in cm (head to toe)"
    )
    wound_size_width = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Wound width in cm (side to side, perpendicular to length)"
    )
    wound_size_depth = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Wound depth in cm (measured at deepest point)"
    )
    
    activate_Account = models.CharField(max_length=50, choices=account_activation_choices, null=True, blank=True, default="Activated")
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self):
        return str(f'{self.first_name} {self.last_name}')
    
    @property
    def wound_surface_area(self):
        """Calculate wound surface area (L × W) in cm²"""
        if self.wound_size_length and self.wound_size_width:
            return float(self.wound_size_length) * float(self.wound_size_width)
        return 0
    
    @property
    def wound_volume(self):
        """Calculate approximate wound volume (L × W × D) in cm³"""
        if self.wound_size_length and self.wound_size_width and self.wound_size_depth:
            return float(self.wound_size_length) * float(self.wound_size_width) * float(self.wound_size_depth)
        return 0
    
    @property
    def latest_ivr(self):
        """Get the most recent IVR form for this patient"""
        return self.ivr_forms.order_by('-submitted_at').first()

    @property
    def latest_ivr_status(self):
        """Get the status of the most recent IVR form"""
        latest = self.latest_ivr
        return latest.status if latest else None

    @property
    def latest_ivr_status_display(self):
        """Get the display name of the most recent IVR status"""
        latest = self.latest_ivr
        return latest.get_status_display() if latest else 'No IVR Submitted'

    @property
    def latest_ivr_pdf_url(self):
        """Get the PDF URL of the most recent IVR form"""
        latest = self.latest_ivr
        if latest and latest.pdf_url:
            from utils.azure_storage import generate_sas_url
            from django.conf import settings
            try:
                return generate_sas_url(
                    blob_name=latest.pdf_blob_name,
                    container_name=settings.AZURE_MEDIA_CONTAINER,
                    permission='r',
                    expiry_hours=72
                )
            except Exception:
                return None
        return None

    @property
    def has_approved_ivr(self):
        """Check if patient has at least one approved IVR"""
        return self.ivr_forms.filter(status='approved').exists()

    @property
    def ivr_count(self):
        """Count total IVR forms for this patient"""
        return self.ivr_forms.count()