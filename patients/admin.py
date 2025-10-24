# patients/admin.py

from django.contrib import admin
from django.db.models import Count # Import Count to aggregate related data
from django.utils import timezone
from .models import Patient, IVRForm # Assuming Patient model is defined here

# -------------------------------------------------------------
# IVRForm Admin (Keep your existing, working configuration)
# -------------------------------------------------------------
@admin.register(IVRForm)
class IVRFormAdmin(admin.ModelAdmin):
    # ... (Your existing IVRFormAdmin implementation) ...
    list_display = [
        'id', 'patient', 'provider', 'status', 'submitted_at', 'reviewed_at', 'reviewed_by'
    ]
    list_filter = ['status', 'submitted_at', 'reviewed_at']
    search_fields = [
        'patient__first_name', 'patient__last_name', 'patient__medical_record_number',
        'provider__first_name', 'provider__last_name', 'provider__email' # Adjusted search field
    ]
    readonly_fields = ['submitted_at', 'updated_at']
    # ... (rest of fieldsets and save_model) ...

# -------------------------------------------------------------
# IVRForm Inline (Keep your existing configuration)
# -------------------------------------------------------------
class IVRFormInline(admin.TabularInline):
    model = IVRForm
    extra = 0
    readonly_fields = ['status', 'submitted_at', 'pdf_url']
    fields = ['status', 'submitted_at', 'pdf_url']
    can_delete = False
    show_change_link = True

# -------------------------------------------------------------
# Enhanced PatientAdmin
# -------------------------------------------------------------
@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    # =================================================================
    # LIST VIEW ENHANCEMENTS (Grouping and Info)
    # =================================================================
    list_display = (
        'full_name',               # Calculated field for display
        'medical_record_number',
        'display_provider',        # Links patient to their provider/physician
        'age',                     # Calculated field for age
        'get_ivr_count',           # Calculated count of IVR forms
        'get_order_count',         # Calculated count of orders
        'city',
        'created_at',
    )
    
    # Enable "grouping" (filtering) by key fields
    list_filter = (
        'provider',        # <-- CRITICAL for grouping by Provider/Physician
        'state',           # Geographical filtering
        'created_at',
    )
    
    search_fields = (
        'first_name',
        'last_name',
        'medical_record_number',
        'provider__first_name',
        'provider__last_name',
        'city',
    )
    
    # Optimizing the QuerySet for the list view
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Use annotate to count related objects efficiently
        qs = qs.annotate(
            ivr_count=Count('ivrform', distinct=True),
            order_count=Count('orders', distinct=True) # Assumes 'orders' is the related_name on the Order model
        ).select_related('provider')
        return qs

    # =================================================================
    # CUSTOM DISPLAY METHODS
    # =================================================================

    @admin.display(description='Patient Name', ordering='last_name')
    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

    @admin.display(description='Provider', ordering='provider__last_name')
    def display_provider(self, obj):
        # Assumes the 'provider' field is a ForeignKey to the User model
        if obj.provider:
            return f"{obj.provider.first_name} {obj.provider.last_name}"
        return "N/A"

    @admin.display(description='Age')
    def age(self, obj):
        if obj.date_of_birth:
            today = timezone.now().date()
            dob = obj.date_of_birth
            # Simple age calculation
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            return f"{age}"
        return "N/A"

    @admin.display(description='IVR Count', ordering='ivr_count')
    def get_ivr_count(self, obj):
        # Access the annotated value from the queryset
        return obj.ivr_count

    @admin.display(description='Order Count', ordering='order_count')
    def get_order_count(self, obj):
        # Access the annotated value from the queryset
        return obj.order_count

    # =================================================================
    # DETAIL VIEW (Adding the IVR Inline)
    # =================================================================
    inlines = [IVRFormInline]
    
    # Organize fields in the detail view
    fieldsets = (
        (None, {
            'fields': (('first_name', 'last_name', 'medical_record_number'), 'provider', 'date_of_birth')
        }),
        ('Contact Information', {
            'fields': ('phone_number', 'email', 'address', ('city', 'state', 'zip_code'))
        }),
        ('Insurance Details', {
            'fields': (
                ('primary_insurance', 'primary_insurance_number'), 
                ('secondary_insurance', 'secondary_insurance_number'),
                ('tertiary_insurance', 'tertiary_insurance_number')
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'age')