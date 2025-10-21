from django.db import models
from django.conf import settings
from patients.models import Patient
# Import the new Product model
from product.models import Product, ProductVariant
from decimal import Decimal


ORDER_STATUS_CHOICES = (
    ('pending', 'Pending'),
    ('processing', 'Processing'),
    ('shipped', 'Shipped'),
    ('delivered', 'Delivered'),
    ('cancelled', 'Cancelled'),
    ('refunded', 'Refunded'),
    ('failed', 'Failed'),
)

# orders/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone # ⬅️ NEW: Import for current year
from patients.models import Patient
from product.models import Product, ProductVariant
from decimal import Decimal


ORDER_STATUS_CHOICES = (
    # ... (Your status choices remain the same)
    ('pending', 'Pending'),
    ('processing', 'Processing'),
    # ...
)

class Order(models.Model):
    provider = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='orders')
    facility_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20)
    street = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=50, choices=ORDER_STATUS_CHOICES, default='pending')
    order_number = models.CharField(max_length=50, unique=True, blank=True, null=True)
    delivery_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new and not self.order_number:
            prefix = "PH"
            year = timezone.now().year
            padded_id = str(self.id).zfill(5) 
            self.order_number = f'{prefix}-{year}-{padded_id}'

            super().save(update_fields=['order_number'])
    def __str__(self):
        # ⬅️ Use the new professional order number here
        return f'{self.order_number} for {self.patient}'
    class Meta:
        db_table = 'orders'

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, related_name='ordered_items')
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, related_name='order_items')
    quantity = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f'{self.quantity} of {self.product.name if self.product else "Deleted Product"}'
    class Meta:
        db_table = 'order_items'

