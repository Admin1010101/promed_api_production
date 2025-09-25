from django.contrib import admin
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.core.mail import send_mail
from django import forms
from django.utils.translation import gettext_lazy as _

from .models import User, Profile, EmailVerificationToken


class ProfileInLine(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'


class AdminUserCreationForm(forms.ModelForm):
    """
    Custom form for creating users in the admin.
    """
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm Password", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ('email', 'full_name', 'role', 'npi_number')

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match.")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInLine,)
    add_form = AdminUserCreationForm

    list_display = (
        'email', 
        'full_name', 
        'role',
        'npi_number',
        'is_verified', 
        'is_approved',
        'is_active', 
        'is_staff',
    )
    search_fields = ('email', 'full_name', 'npi_number')
    list_filter = ('is_verified', 'is_approved', 'is_staff', 'is_active', 'role')
    readonly_fields = ('date_joined',)
    ordering = ('-date_joined',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('full_name', 'phone_number', 'npi_number')}),
        ('Permissions', {
            'fields': (
                'role',
                'is_active', 
                'is_approved', 
                'is_staff', 
                'is_superuser', 
                'groups', 
                'user_permissions'
            )
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return []
        return super().get_inline_instances(request, obj)

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'role', 'npi_number', 'password1', 'password2'),
        }),
    )

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets
        return super().get_fieldsets(request, obj)

    def save_model(self, request, obj, form, change):
        is_new = obj.pk is None

        # If not using the creation form, ensure password is hashed manually
        if 'password' in form.cleaned_data and not form.cleaned_data['password'].startswith('pbkdf2_'):
            obj.set_password(form.cleaned_data['password'])

        super().save_model(request, obj, form, change)

        if is_new and not obj.is_verified:
            # Send verification email
            token, _ = EmailVerificationToken.objects.get_or_create(user=obj)
            verification_link = f"https://wchandler2020.github.io/promedhealthplus_portal_client/#/verify-email/{token.token}"

            html_message = render_to_string('provider_auth/email_verification.html', {
                'user': obj,
                'verification_link': verification_link
            })

            send_mail(
                subject='Verify Your Email Address',
                message=f"Click the link to verify your email: {verification_link}",
                html_message=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[obj.email],
                fail_silently=False
            )