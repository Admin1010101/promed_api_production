from django.db import models
from django.conf import settings
from phonenumber_field.modelfields import PhoneNumberField

ivr_status_choices = (("Pending", "Pending"), ("Approved", "Approved"), ("Denied", "Denied"))

account_activation_choices = (("Activated", "Activated"), ("Deactivated", "Deactivated"))

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
    wound_size_length = models.PositiveIntegerField(null=True, blank=True)
    wound_size_width = models.PositiveIntegerField(null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    # Adding new models from what we had before?
    ivrStatus = models.CharField(max_length=50, choices=ivr_status_choices, null=True, blank=True)
    activate_Account = models.CharField(max_length=50, choices=account_activation_choices, null=True, blank=True, default="Activated")

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self):
        return str(f'{self.first_name} {self.last_name}')

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"