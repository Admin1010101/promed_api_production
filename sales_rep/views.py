# sales_rep/views.py
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from provider_auth.models import Profile, User
from sales_rep.models import SalesRep
from patients.models import IVRForm, Patient
from orders.models import Order
from .serializers import SalesRepDashboardSerializer
from itertools import chain
from operator import attrgetter
import logging

logger = logging.getLogger(__name__)


class SalesRepDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            sales_rep = request.user.salesrep_profile
        except SalesRep.DoesNotExist:
            return Response(
                {"error": "You are not associated with a SalesRep profile."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = SalesRepDashboardSerializer(sales_rep)
        return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sales_rep_dashboard_stats(request):
    """Get dashboard statistics for a sales representative"""
    
    try:
        # Get the SalesRep profile for current user
        sales_rep = SalesRep.objects.filter(user=request.user).first()
        
        if not sales_rep:
            return Response({
                "error": "Sales Rep profile not found for this user"
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get all providers assigned to this sales rep
        assigned_providers = Profile.objects.filter(
            sales_rep=sales_rep
        ).select_related('user')
        
        provider_count = assigned_providers.count()
        
        # Get provider user IDs for querying related data
        provider_user_ids = list(assigned_providers.values_list('user_id', flat=True))
        
        # Build recent activities from multiple sources
        recent_activities = []
        
        # 1. IVR Form submissions
        recent_ivr_forms = IVRForm.objects.filter(
            provider_id__in=provider_user_ids
        ).select_related('provider', 'patient').order_by('-submitted_at')[:10]
        
        for ivr in recent_ivr_forms:
            recent_activities.append({
                'id': f'ivr_{ivr.id}',
                'type': 'IVR Form',
                'description': f'{ivr.get_status_display()}',
                'name': ivr.provider.full_name or ivr.provider.email,
                'detail': f'Patient: {ivr.patient.first_name} {ivr.patient.last_name}',
                'date': ivr.submitted_at,
                'date_formatted': ivr.submitted_at.strftime('%b %d, %Y %I:%M %p') if ivr.submitted_at else 'N/A',
                'status': ivr.status,
                'icon': 'document',
            })
        
        # 2. Orders placed
        try:
            recent_orders = Order.objects.filter(
                provider_id__in=provider_user_ids
            ).select_related('provider').order_by('-created_at')[:10]
            
            for order in recent_orders:
                recent_activities.append({
                    'id': f'order_{order.id}',
                    'type': 'Order Placed',
                    'description': f'Order #{order.id}',
                    'name': order.provider.full_name or order.provider.email,
                    'detail': f'Status: {order.status}' if hasattr(order, 'status') else '',
                    'date': order.created_at,
                    'date_formatted': order.created_at.strftime('%b %d, %Y %I:%M %p') if order.created_at else 'N/A',
                    'status': getattr(order, 'status', 'placed'),
                    'icon': 'cart',
                })
        except Exception as e:
            logger.warning(f"Could not fetch orders: {str(e)}")
        
        # 3. Patients added
        try:
            recent_patients = Patient.objects.filter(
                provider_id__in=provider_user_ids
            ).select_related('provider').order_by('-created_at')[:10]
            
            for patient in recent_patients:
                recent_activities.append({
                    'id': f'patient_{patient.id}',
                    'type': 'Patient Added',
                    'description': 'New patient registered',
                    'name': patient.provider.full_name or patient.provider.email,
                    'detail': f'Patient: {patient.first_name} {patient.last_name}',
                    'date': patient.created_at,
                    'date_formatted': patient.created_at.strftime('%b %d, %Y %I:%M %p') if patient.created_at else 'N/A',
                    'status': 'added',
                    'icon': 'person',
                })
        except Exception as e:
            logger.warning(f"Could not fetch patients: {str(e)}")
        
        # 4. BAA signed
        try:
            baa_signed_users = User.objects.filter(
                id__in=provider_user_ids,
                has_signed_baa=True,
                baa_signed_at__isnull=False
            ).order_by('-baa_signed_at')[:10]
            
            for user in baa_signed_users:
                recent_activities.append({
                    'id': f'baa_{user.id}',
                    'type': 'BAA Signed',
                    'description': 'Business Associate Agreement completed',
                    'name': user.full_name or user.email,
                    'detail': 'Compliance document signed',
                    'date': user.baa_signed_at,
                    'date_formatted': user.baa_signed_at.strftime('%b %d, %Y %I:%M %p') if user.baa_signed_at else 'N/A',
                    'status': 'completed',
                    'icon': 'checkmark',
                })
        except Exception as e:
            logger.warning(f"Could not fetch BAA data: {str(e)}")
        
        # Sort all activities by date (most recent first)
        recent_activities = sorted(
            recent_activities,
            key=lambda x: x['date'] if x['date'] else '',
            reverse=True
        )[:15]  # Limit to 15 most recent
        
        # Build providers list
        providers_list = []
        for profile in assigned_providers:
            providers_list.append({
                'id': profile.user.id,
                'name': profile.user.full_name or profile.user.username,
                'email': profile.user.email,
                'phone': str(profile.user.phone_number) if profile.user.phone_number else '',
                'facility': profile.user.facility or '',
                'is_verified': profile.user.is_verified,
                'is_approved': profile.user.is_approved,
                'has_signed_baa': profile.user.has_signed_baa,
                'date_joined': profile.user.date_joined.strftime('%b %d, %Y'),
            })
        
        return Response({
            'success': True,
            'stats': {
                'total_providers': provider_count,
                'active_providers': provider_count,
            },
            'providers': providers_list,
            'recent_activities': recent_activities,
            'sales_rep': {
                'id': sales_rep.id,
                'name': sales_rep.name,
                'email': sales_rep.email,
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching sales rep dashboard: {str(e)}", exc_info=True)
        return Response({
            "error": "Failed to fetch dashboard data",
            "detail": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)