from django.contrib import admin
from .models import Patient, IVRForm
@admin.register(IVRForm)
class IVRFormAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'patient',
        'provider',
        'status',
        'submitted_at',
        'reviewed_at',
        'reviewed_by'
    ]
    list_filter = ['status', 'submitted_at', 'reviewed_at']
    search_fields = [
        'patient__first_name',
        'patient__last_name',
        'patient__medical_record_number',
        'provider__full_name',
        'provider__email'
    ]
    readonly_fields = ['submitted_at', 'updated_at']
    
    fieldsets = (
        ('Patient & Provider', {
            'fields': ('patient', 'provider')
        }),
        ('IVR Details', {
            'fields': (
                'physician_name',
                'contact_name',
                'phone',
                'facility_address',
                'facility_city_state_zip',
                'wound_size_length',
                'wound_size_width',
            )
        }),
        ('PDF Storage', {
            'fields': ('pdf_url', 'pdf_blob_name')
        }),
        ('Status', {
            'fields': ('status', 'admin_notes', 'reviewed_by', 'reviewed_at')
        }),
        ('Timestamps', {
            'fields': ('submitted_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Automatically set reviewed_by when admin changes status"""
        if change and 'status' in form.changed_data:
            if obj.status in ['approved', 'denied', 'cancelled']:
                from django.utils import timezone
                obj.reviewed_by = request.user
                obj.reviewed_at = timezone.now()
        super().save_model(request, obj, form, change)


# Update your existing PatientAdmin to show IVR count
class IVRFormInline(admin.TabularInline):
    model = IVRForm
    extra = 0
    readonly_fields = ['status', 'submitted_at', 'pdf_url']
    fields = ['status', 'submitted_at', 'pdf_url']
    can_delete = False
    show_change_link = True


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    inlines = [IVRFormInline]
    # ... rest of your existing PatientAdmin configuration
