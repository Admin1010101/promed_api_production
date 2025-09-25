from django.db import models
class Product(models.Model):
    name = models.CharField(max_length=255, unique=True)
    manufacturer = models.CharField(max_length=155, null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(
        upload_to='product_images/', 
        null=True, 
        blank=True, 
        default='images/default_item.png'
    )
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} by {self.manufacturer}"
    class Meta:
        db_table = 'products'
        ordering = ['name']

class ProductVariant(models.Model):
    product = models.ForeignKey(Product, related_name="variants", on_delete=models.CASCADE)
    size = models.CharField(max_length=50)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.product.name} - {self.size}"
    class Meta:
        unique_together = ('product', 'size')
        ordering = ['product', 'size']
