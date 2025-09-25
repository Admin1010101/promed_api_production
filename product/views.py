from rest_framework import generics, permissions
from django.db.models import Prefetch
from .models import Product, ProductVariant
from .serializers import ProductSerializer

class ProductListView(generics.ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Product.objects.filter(is_available=True).prefetch_related(
            Prefetch('variants', queryset=ProductVariant.objects.filter(is_available=True))
        )
