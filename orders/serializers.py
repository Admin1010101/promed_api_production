from rest_framework import serializers
from .models import Order, OrderItem
from product.models import Product, ProductVariant
from patients.models import Patient, WOUND_TYPE_CHOICES
from django.urls import reverse


class OrderItemSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    variant = serializers.PrimaryKeyRelatedField(queryset=ProductVariant.objects.all())

    class Meta:
        model = OrderItem
        fields = ['product', 'variant', 'quantity']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = '__all__'
        read_only_fields = ['id', 'provider', 'status', 'created_at']

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        user = self.context['request'].user
        order = Order.objects.create(
            provider=user,
            **validated_data
        )
        for item_data in items_data:
            OrderItem.objects.create(
                order=order,
                product=item_data['product'],
                variant=item_data['variant'],
                quantity=item_data['quantity'],
            )
        return order


class OrderSummarySerializer(serializers.ModelSerializer):
    invoice_url = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['id', 'created_at', 'status', 'invoice_url']

    def get_invoice_url(self, obj):
        request = self.context.get('request')
        if not request:
            return None
        path = reverse('order-invoice-pdf', args=[obj.id])
        return request.build_absolute_uri(path)


class PatientOrderHistorySerializer(serializers.ModelSerializer):
    orders = serializers.SerializerMethodField()
    total_orders_count = serializers.SerializerMethodField()  # ✅ NEW: Total count

    class Meta:
        model = Patient
        fields = ['id', 'first_name', 'last_name', 'orders', 'total_orders_count', 'activate_Account']

    def get_total_orders_count(self, obj):
        """Return total number of orders for this patient"""
        return obj.orders.count()

    def get_orders(self, obj):
        request = self.context.get('request')
        if not request:
            return []
        
        # Check if we should return all orders or just the latest 5
        all_orders = request.query_params.get('all', 'false').lower() == 'true'
        
        qs = obj.orders.order_by('-created_at')
        if not all_orders:
            qs = qs[:5]  # Return only the 5 most recent
        
        return OrderSummarySerializer(qs, many=True, context=self.context).data
    



class CareKitOrderSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for CareKit orders with all Conservative Care fields.
    Used for displaying orders in the Conservative Care dashboard.
    """
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    patient_first_name = serializers.CharField(source='patient.first_name', read_only=True)
    patient_last_name = serializers.CharField(source='patient.last_name', read_only=True)
    provider_name = serializers.SerializerMethodField()
    
    # Display fields for choice fields
    wound_type_display = serializers.CharField(source='get_wound_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    kit_size_display = serializers.CharField(source='get_kit_size_display', read_only=True)
    kit_duration_display = serializers.CharField(source='get_kit_duration_display', read_only=True)
    wound_drainage_display = serializers.CharField(source='get_wound_drainage_display', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id',
            'order_number',
            'provider',
            'provider_name',
            'patient',
            'patient_name',
            'patient_first_name',
            'patient_last_name',
            
            # Wound information
            'wound_type',
            'wound_type_display',
            'wound_location',
            'is_chronic_wound',
            'wound_drainage',
            'wound_drainage_display',
            'conservative_care',
            'icd10_code',
            
            # Kit details
            'kit_duration',
            'kit_duration_display',
            'kit_size',
            'kit_size_display',
            'recommended_kit',
            
            # Order details
            'status',
            'status_display',
            'tracking_number',
            'facility_name',
            'phone_number',
            'street',
            'city',
            'zip_code',
            'country',
            
            # Timestamps
            'created_at',
            'shipped_at',
            'delivery_date',
            'updated_at',
        ]
        read_only_fields = ['id', 'order_number', 'created_at', 'updated_at', 'provider']
    
    def get_provider_name(self, obj):
        """Get provider's full name"""
        if hasattr(obj.provider, 'full_name'):
            return obj.provider.full_name
        return f"{obj.provider.first_name} {obj.provider.last_name}" if hasattr(obj.provider, 'first_name') else obj.provider.email


class CareKitOrderCreateSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for creating CareKit orders from Conservative Care dashboard.
    Only includes the fields needed for order creation.
    """
    
    class Meta:
        model = Order
        fields = [
            'patient',
            
            # Wound details
            'wound_type',
            'wound_location',
            'is_chronic_wound',
            'wound_drainage',
            'conservative_care',
            'icd10_code',
            
            # Kit details
            'kit_duration',
            'kit_size',
            
            # Facility/shipping details
            'facility_name',
            'phone_number',
            'street',
            'city',
            'zip_code',
            'country',
        ]
    
    def validate(self, data):
        """Custom validation for required fields"""
        # Ensure patient exists
        if not data.get('patient'):
            raise serializers.ValidationError({'patient': 'Patient is required'})
        
        # Ensure kit details are provided
        if not data.get('kit_duration'):
            raise serializers.ValidationError({'kit_duration': 'Kit duration is required'})
        
        if not data.get('kit_size'):
            raise serializers.ValidationError({'kit_size': 'Kit size is required'})
        
        return data
    
    def create(self, validated_data):
        """Create order with auto-generated fields"""
        # Auto-generate recommended kit description
        kit_duration = validated_data.get('kit_duration', '30-day')
        kit_size = validated_data.get('kit_size', '2x2')
        wound_type = validated_data.get('wound_type', '')
        
        # Get wound type display name
        wound_display = dict(WOUND_TYPE_CHOICES).get(wound_type, wound_type.upper()) if wound_type else 'CareKit'
        validated_data['recommended_kit'] = f"{kit_duration} {wound_display} Kit - {kit_size}"
        
        # Set provider from request context
        validated_data['provider'] = self.context['request'].user
        
        # Set initial status
        validated_data['status'] = 'pending'
        
        return super().create(validated_data)


class CareKitOrderListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing orders in the Recent Activity table.
    Only includes essential fields for the dashboard table.
    """
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    wound_type_display = serializers.CharField(source='get_wound_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id',
            'order_number',
            'patient',
            'patient_name',
            'wound_type',
            'wound_type_display',
            'status',
            'status_display',
            'created_at',
            'tracking_number',
        ]
        read_only_fields = ['id', 'order_number', 'created_at']











































