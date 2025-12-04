from django.contrib import admin
from django.db.models import Sum
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['product', 'variant']
    fields = ('product', 'variant', 'quantity')
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_number',
        'patient_full_name',
        'provider_name',
        'total_items_ordered',
        'status',
        'created_at',
        'delivery_date',
    )

    list_filter = (
        'status',
        'created_at',
        'delivery_date',
    )

    # Not static anymore — handled dynamically in get_list_editable()
    list_editable = ()

    inlines = [OrderItemInline]

    readonly_fields = ('order_number', 'created_at', 'updated_at')

    actions = ['mark_as_delivered']

    class Media:
        js = ('admin/js/disable_delivered.js',)

    # ------------------------------------------------------------ #
    # 1. Disable editing of delivered rows in list view
    # ------------------------------------------------------------ #
    def get_list_editable(self, request):
        return ('status',)

    def get_changelist_formset(self, request, **kwargs):
        formset = super().get_changelist_formset(request, **kwargs)

        class DeliveredLockedFormset(formset):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                for form in self.forms:
                    instance = form.instance
                    if instance and instance.status == 'delivered':
                        if 'status' in form.fields:
                            form.fields['status'].disabled = True

        return DeliveredLockedFormset

    # ------------------------------------------------------------ #
    # 2. Disable editing in detail view for delivered orders
    # ------------------------------------------------------------ #
    def get_readonly_fields(self, request, obj=None):
        if obj and obj.status == 'delivered':
            return (
                'order_number', 'status', 'provider', 'patient',
                'created_at', 'updated_at', 'delivery_date',
                'facility_name', 'phone_number', 'street',
                'city', 'zip_code', 'country'
            )
        return self.readonly_fields

    def save_model(self, request, obj, form, change):
        if obj.pk:
            old_obj = Order.objects.get(pk=obj.pk)
            if old_obj.status == 'delivered' and obj.status != old_obj.status:
                self.message_user(request, "Delivered orders cannot be modified.", level='error')
                return
        super().save_model(request, obj, form, change)

    # ------------------------------------------------------------ #
    # 3. Admin Action — Mark as Delivered
    # ------------------------------------------------------------ #
    def mark_as_delivered(self, request, queryset):
        not_delivered = queryset.exclude(status='delivered')
        updated = not_delivered.update(status='delivered')
        skipped = queryset.count() - updated

        msg = f"{updated} order(s) marked as Delivered."
        if skipped:
            msg += f" ({skipped} already delivered → skipped)"
        self.message_user(request, msg)
    mark_as_delivered.short_description = "Mark selected orders as Delivered"

    # ------------------------------------------------------------ #
    # 4. Display helpers
    # ------------------------------------------------------------ #
    @admin.display(description='Patient')
    def patient_full_name(self, obj):
        return f"{obj.patient.first_name} {obj.patient.last_name}"

    @admin.display(description='Provider/Physician')
    def provider_name(self, obj):
        return f"{obj.provider.first_name} {obj.provider.last_name}"

    @admin.display(description='Total Items', ordering='_total_items')
    def total_items_ordered(self, obj):
        return obj._total_items or 0

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_total_items=Sum('items__quantity')).select_related('patient', 'provider')