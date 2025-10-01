# notifications/admin.py
from django.contrib import admin
from django import forms
from .models import Notification
from provider_auth.models import User

class NotificationAdminForm(forms.ModelForm):
    send_to_all = forms.BooleanField(required=False, help_text="Check to send this notification to all users.")

    class Meta:
        model = Notification
        fields = '__all__'

class NotificationAdmin(admin.ModelAdmin):
    form = NotificationAdminForm

    def save_model(self, request, obj, form, change):
        send_to_all = form.cleaned_data.get('send_to_all')
        if send_to_all:
            users = User.objects.all()
            notifications = [
                Notification(
                    recipient=user,
                    message=obj.message,
                    type=obj.type,
                    data=obj.data,
                    broadcast=True
                )
                for user in users
            ]
            Notification.objects.bulk_create(notifications)
        else:
            # Save normally for one recipient
            super().save_model(request, obj, form, change)
            
admin.site.register(Notification, NotificationAdmin)
            