# sales_rep/admin.py
from django.contrib import admin
from django import forms
from .models import SalesRep
from provider_auth.models import Profile


class SalesRepAdminForm(forms.ModelForm):
    """Custom form with multi-select for assigning providers"""
    
    assigned_providers = forms.ModelMultipleChoiceField(
        queryset=Profile.objects.filter(user__role='provider'),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Assigned Providers/Doctors"
    )
    
    class Meta:
        model = SalesRep
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Pre-select providers already assigned to this sales rep
        if self.instance and self.instance.pk:
            self.fields['assigned_providers'].initial = Profile.objects.filter(
                sales_rep=self.instance
            )
        
        # Customize the queryset with user data
        self.fields['assigned_providers'].queryset = Profile.objects.filter(
            user__role='provider'
        ).select_related('user')
        
        # Custom label for each checkbox
        self.fields['assigned_providers'].label_from_instance = lambda obj: (
            f"{obj.user.full_name or obj.user.username} ({obj.user.email})"
        )
    
    def save_m2m(self):
        """Handle the many-to-many-like relationship"""
        pass  # We handle this in save_related below
    
    def save(self, commit=True):
        return super().save(commit=commit)


@admin.register(SalesRep)
class SalesRepAdmin(admin.ModelAdmin):
    form = SalesRepAdminForm
    
    list_display = ['name', 'email', 'phone', 'user', 'provider_count', 'date_created']
    list_filter = ['date_created']
    search_fields = ['name', 'email', 'user__email']
    readonly_fields = ['date_created', 'date_updated']
    
    fieldsets = (
        ('Sales Rep Information', {
            'fields': ('user', 'name', 'email', 'phone')
        }),
        ('Assigned Providers', {
            'fields': ('assigned_providers',),
            'description': 'Select providers/doctors to assign to this sales representative.'
        }),
        ('Timestamps', {
            'fields': ('date_created', 'date_updated'),
            'classes': ('collapse',)
        }),
    )
    
    def provider_count(self, obj):
        """Show count of assigned providers"""
        return Profile.objects.filter(sales_rep=obj).count()
    provider_count.short_description = 'Assigned Providers'
    
    def save_related(self, request, form, formsets, change):
        """Handle provider assignments after the main object is saved"""
        super().save_related(request, form, formsets, change)
        
        # Get the saved instance
        instance = form.instance
        
        # Get selected providers
        selected_providers = form.cleaned_data.get('assigned_providers', [])
        selected_pks = [p.pk for p in selected_providers]
        
        # Remove sales rep from unselected providers
        Profile.objects.filter(sales_rep=instance).exclude(pk__in=selected_pks).update(sales_rep=None)
        
        # Assign sales rep to selected providers
        if selected_pks:
            Profile.objects.filter(pk__in=selected_pks).update(sales_rep=instance)