from django.contrib import admin
from .models import Product, ProductVariant

# Register your models here.

admin.site.register(Product)
admin.site.register(ProductVariant)
