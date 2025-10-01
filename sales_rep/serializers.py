from rest_framework import serializers
from provider_auth.models import Profile, User
from patients.models import Patient
from orders.models import Order
from sales_rep.models import SalesRep


# Order serializer
class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['id', 'status', 'created_at']


# Patient serializer with ivrStatus and orders
class PatientSerializer(serializers.ModelSerializer):
    orders = OrderSerializer(many=True, read_only=True)

    class Meta:
        model = Patient
        fields = ['id', 'full_name', 'ivrStatus', 'orders']


# Provider serializer with patients list
class ProviderDashboardSerializer(serializers.ModelSerializer):
    patients = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ['id', 'full_name', 'patients']

    def get_patients(self, obj):
        try:
            user = obj.user
            patients = user.patients.all()
            return PatientSerializer(patients, many=True).data
        except User.DoesNotExist:
            return []


# Main Dashboard Serializer
class SalesRepDashboardSerializer(serializers.ModelSerializer):
    providers = ProviderDashboardSerializer(many=True, read_only=True)
    stats = serializers.SerializerMethodField()

    class Meta:
        model = SalesRep
        fields = ['id', 'name', 'providers', 'stats']

    def get_stats(self, obj):
        provider_stats = []
        total_orders = 0
        total_delivered = 0
        total_ivrs = 0
        total_approved_ivrs = 0

        for provider in obj.providers.all():
            try:
                user = provider.user
                patients = user.patients.all()
            except User.DoesNotExist:
                patients = []

            provider_orders = 0
            provider_delivered = 0
            provider_ivrs = 0
            provider_approved_ivrs = 0

            for patient in patients:
                # Count orders
                orders = patient.orders.all()
                provider_orders += orders.count()
                provider_delivered += orders.filter(status='Delivered').count()

                # Count IVRs (only one per patient for now)
                if patient.ivrStatus:
                    provider_ivrs += 1
                    if patient.ivrStatus == 'Approved':
                        provider_approved_ivrs += 1

            provider_stats.append({
                'provider_id': provider.id,
                'provider_name': provider.full_name,
                'total_orders': provider_orders,
                'delivered_orders': provider_delivered,
                'total_ivrs': provider_ivrs,
                'approved_ivrs': provider_approved_ivrs,
            })

            total_orders += provider_orders
            total_delivered += provider_delivered
            total_ivrs += provider_ivrs
            total_approved_ivrs += provider_approved_ivrs

        return {
            'summary': {
                'totalOrders': total_orders,
                'deliveredOrders': total_delivered,
                'totalIVRs': total_ivrs,
                'approvedIVRs': total_approved_ivrs,
            },
            'by_provider': provider_stats,
        }

