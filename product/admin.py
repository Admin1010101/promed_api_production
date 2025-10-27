# product/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count
from .models import Product, ProductVariant

# --- 1. Inline for Product Variants ---
class ProductVariantInline(admin.TabularInline):
    """Allows ProductVariants to be managed directly within the Product admin page."""
    model = ProductVariant
    extra = 1  # Show one extra blank form for adding a new variant
    fields = ('size', 'is_available')
    verbose_name = 'Variant'
    verbose_name_plural = 'Product Variants'

    # Optional: Limit fields if needed, but usually all fields are relevant for variants
    # readonly_fields = ('some_calculated_field',)


# --- 2. Custom Product Admin Model ---
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    # =================================================================
    # LIST VIEW ENHANCEMENTS
    # =================================================================
    list_display = (
        'name',
        'manufacturer',
        'display_image',           # Custom method to show a thumbnail
        'variant_count',           # Custom method showing total variants
        'is_available',
        'created_at',
    )

    list_filter = (
        'is_available',
        'manufacturer',
        'created_at',
    )

    search_fields = (
        'name',
        'manufacturer',
        'description',
        'variants__size',  # Allows searching by variant size!
    )

    ordering = ('name',)

    # =================================================================
    # DETAIL/EDIT VIEW ENHANCEMENTS
    # =================================================================

    # Add the variants to the detail page using the inline
    inlines = [ProductVariantInline]

    # Organize fields into fieldsets
    fieldsets = (
        (None, {
            'fields': (('name', 'manufacturer'), 'description', 'is_available', 'product_url', 'image')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ('created_at', 'updated_at')

    # Prefetch and Annotate for list view performance
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Annotate with the count of related product variants
        qs = qs.annotate(
            _variant_count=Count('variants', distinct=True)
        )
        return qs

    # =================================================================
    # CUSTOM DISPLAY METHODS
    # =================================================================

    @admin.display(description='Variants', ordering='_variant_count')
    def variant_count(self, obj):
        # Access the annotated value
        return obj._variant_count

    @admin.display(description='Image')
    def display_image(self, obj):
        if obj.image and hasattr(obj.image, 'url'):
            # Display a small thumbnail in the list view
            return format_html('<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px;" />', obj.image.url)
        return "No Image"
    
admin.site.register(ProductVariant)

# NOTE: Remove the simple admin.site.register(Product) and admin.site.register(ProductVariant)
# The @admin.register(Product) decorator replaces it for the Product model.
# The ProductVariant is handled via the inline.