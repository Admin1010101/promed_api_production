# orders/admin.py

from django.contrib import admin
from django.db.models import F, Sum
from django.urls import reverse
from django.utils.html import format_html
from .models import Order, OrderItem

# --- 1. Inline for Order Items ---
class OrderItemInline(admin.TabularInline):
    """Allows OrderItems to be edited directly within the Order admin page."""
    model = OrderItem
    raw_id_fields = ['product', 'variant']
    # Exclude or make readonly the fields you don't want admins to change
    fields = ('product', 'variant', 'quantity')
    extra = 0 # Don't show extra blank forms by default
    verbose_name = 'Product Ordered'
    verbose_name_plural = 'Products Ordered'

    def get_queryset(self, request):
        # Optional: Prefetch related data for performance
        return super().get_queryset(request).select_related('product', 'variant')


# --- 2. Custom Order Admin Model ---
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    # =================================================================
    # LIST VIEW ENHANCEMENTS (Your Request)
    # =================================================================

    # 1. Columns to Display
    list_display = (
        'order_number',         # The unique order number
        'patient_full_name',    # Custom method for patient name
        'provider_name',        # Custom method for provider name
        'total_items_ordered',  # Custom method for quantity summary
        'status',               # The order status
        'created_at',           # When the order was created/submitted
        'delivery_date',        # Requested delivery date
    )
    
    # 2. Filters (The 'Grouping' Mechanism)
    list_filter = (
        'provider',             # <-- Groups/Filters by Provider/Physician
        'status',               # Filter by order status
        'created_at',           # Filter by date/month/year created
        'delivery_date',        # Filter by delivery date
    )
    
    # 3. Search Fields
    search_fields = (
        'order_number',
        'patient__first_name',
        'patient__last_name',
        'provider__first_name',
        'provider__last_name',
        'facility_name',
        'phone_number',
    )
    
    # 4. Sorting
    ordering = ('-created_at',)
    
    # =================================================================
    # DETAIL/EDIT VIEW ENHANCEMENTS
    # =================================================================
    
    # Organize fields into fieldsets
    fieldsets = (
        ('Order Details', {
            'fields': ('order_number', 'status', 'delivery_date', 'created_at'),
        }),
        ('Provider and Patient', {
            'fields': ('provider', 'patient'),
        }),
        ('Shipping Information', {
            'fields': ('facility_name', 'phone_number', 'street', 'city', 'zip_code', 'country'),
        }),
    )

    # Display OrderItemInline on the Order detail page
    inlines = [
        OrderItemInline,
    ]
    
    # Fields that should be read-only in the edit view
    readonly_fields = ('order_number', 'created_at', 'updated_at')

    # Prefetch related data for better detail view performance
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Annotate with the total quantity of items
        qs = qs.annotate(
            _total_items = Sum('items__quantity')
        ).select_related('patient', 'provider')
        return qs

    # =================================================================
    # CUSTOM DISPLAY METHODS
    # =================================================================
    
    @admin.display(description='Patient')
    def patient_full_name(self, obj):
        return f"{obj.patient.first_name} {obj.patient.last_name}"
    
    @admin.display(description='Provider/Physician')
    def provider_name(self, obj):
        # Assuming your User model has first_name and last_name
        return f"{obj.provider.first_name} {obj.provider.last_name}"

    @admin.display(description='Total Items', ordering='_total_items')
    def total_items_ordered(self, obj):
        # Access the annotated value
        return obj._total_items or 0
    
admin.site.register(OrderItem)

# NOTE: Remove the simple admin.site.register(Order) if you use the decorator
# admin.site.register(Order, OrderAdmin)