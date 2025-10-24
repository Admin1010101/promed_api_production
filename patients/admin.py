# patients/admin.py

from django.contrib import admin
from django.db.models import Count
from django.utils import timezone
from .models import Patient, IVRForm # Import Patient and IVRForm

# -------------------------------------------------------------
# IVRForm Admin (No changes needed, kept for completeness)
# -------------------------------------------------------------
@admin.register(IVRForm)
class IVRFormAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'patient', 'provider', 'status', 'submitted_at', 'reviewed_at', 'reviewed_by'
    ]
    list_filter = ['status', 'submitted_at', 'reviewed_at']
    search_fields = [
        'patient__first_name', 'patient__last_name', 'patient__medical_record_number',
        'provider__first_name', 'provider__last_name', 'provider__email'
    ]
    readonly_fields = ['submitted_at', 'updated_at']
    # ... (rest of fieldsets and save_model) ...

# -------------------------------------------------------------
# IVRForm Inline
# -------------------------------------------------------------
class IVRFormInline(admin.TabularInline):
    model = IVRForm
    extra = 0
    readonly_fields = ['status', 'submitted_at', 'pdf_url']
    fields = ['status', 'submitted_at', 'pdf_url']
    can_delete = False
    show_change_link = True

# -------------------------------------------------------------
# Enhanced PatientAdmin (Ready to run after model fix)
# -------------------------------------------------------------
@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = (
        'full_name',
        'medical_record_number',
        'display_provider',
        'age',
        'get_ivr_count',
        'get_order_count',
        'city',
        'created_at', # ⬅️ Now exists on the model
    )

    list_filter = (
        'provider',
        'state',
        'created_at', # ⬅️ Now exists on the model
    )

    search_fields = (
        'first_name',
        'last_name',
        'medical_record_number',
        'provider__first_name',
        'provider__last_name',
        'city',
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.annotate(
            ivr_count=Count('ivrform', distinct=True),
            order_count=Count('orders', distinct=True)
        ).select_related('provider')
        return qs

    @admin.display(description='Patient Name', ordering='last_name')
    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

    @admin.display(description='Provider', ordering='provider__last_name')
    def display_provider(self, obj):
        if obj.provider:
            return f"{obj.provider.first_name} {obj.provider.last_name}"
        return "N/A"

    @admin.display(description='Age')
    def age(self, obj):
        if obj.date_of_birth:
            today = timezone.now().date()
            dob = obj.date_of_birth
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            return f"{age}"
        return "N/A"

    @admin.display(description='IVR Count', ordering='ivr_count')
    def get_ivr_count(self, obj):
        return obj.ivr_count

    @admin.display(description='Order Count', ordering='order_count')
    def get_order_count(self, obj):
        return obj.order_count

    inlines = [IVRFormInline]

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
            'fields': ('created_at', 'updated_at'), # ⬅️ Now functional
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ('created_at', 'updated_at', 'age') # ⬅️ Now functional