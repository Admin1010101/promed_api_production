# orders/views.py
from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from django.http import FileResponse, Http404
from django.conf import settings
from django.template.loader import render_to_string
from xhtml2pdf import pisa
from io import BytesIO
from django.core.mail import EmailMessage
import orders.serializers as api_serializers
import orders.models as api_models
from rest_framework.response import Response
from decimal import Decimal
import re  
import logging

logger = logging.getLogger(__name__)

# Import Azure functions properly
try:
    from utils.azure_storage import get_blob_service_client
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    logger.warning("⚠️ utils.azure_storage not available - using fallback")


def clean_string(text):
    """Clean string for use in file paths."""
    if not text:
        return "unknown"
    return "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in text).strip()


def generate_pdf_from_html(html_content):
    """Generates a PDF file from HTML content using xhtml2pdf."""
    result_file = BytesIO()
    pisa_status = pisa.pisaDocument(
        BytesIO(html_content.encode("UTF-8")),
        dest=result_file
    )
    if not pisa_status.err:
        result_file.seek(0)
        return result_file
    print(f"xhtml2pdf error encountered: {pisa_status.err}")
    return None


def parse_variant_size_to_cm2(size_str):
    """
    Parse variant size string and return area in cm².
    Handles formats like:
    - "2 x 2" (assumes cm)
    - "2 x 2 cm"
    - "20 x 20 mm" (converts to cm)
    """
    if not size_str:
        return Decimal('0')
    
    try:
        # Match: number x number with optional unit (mm or cm)
        match = re.match(r'(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*(mm|cm)?', size_str, re.IGNORECASE)
        if not match:
            logger.warning(f"⚠️ Could not parse size: {size_str}")
            return Decimal('0')
        
        length = Decimal(match.group(1))
        width = Decimal(match.group(2))
        unit = match.group(3).lower() if match.group(3) else 'cm'  # Default to cm
        
        # Convert mm to cm (1cm = 10mm)
        if unit == 'mm':
            length = length / Decimal('10')
            width = width / Decimal('10')
        
        return length * width  # Return area in cm²
    except Exception as e:
        logger.error(f"❌ Error parsing size '{size_str}': {e}")
        return Decimal('0')


class CreateOrderView(generics.CreateAPIView):
    serializer_class = api_serializers.OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        logger.info("="*50)
        logger.info("🛒 CREATE ORDER REQUEST")
        logger.info(f"User: {request.user.email}")
        logger.info(f"Data: {request.data}")
        logger.info("="*50)
        
        data = request.data.copy()
        data['provider'] = request.user.id

        # Get the patient
        patient_id = data.get('patient')
        if not patient_id:
            return Response(
                {'error': 'Patient ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            from patients.models import Patient
            patient = Patient.objects.get(id=patient_id, provider=request.user)
        except Patient.DoesNotExist:
            return Response(
                {'error': 'Patient not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # ✅ Check IVR status
        if not patient.has_approved_ivr:
            latest_ivr_status = patient.latest_ivr_status_display if patient.latest_ivr else "No IVR Submitted"
            logger.warning(f"❌ Order blocked: Patient {patient.id} has no approved IVR. Latest status: {latest_ivr_status}")
            return Response(
                {
                    'error': 'Cannot place order',
                    'detail': f'Patient must have an approved IVR to place orders. Current status: {latest_ivr_status}'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ✅ Check wound size exists
        if not patient.wound_size_length or not patient.wound_size_width:
            logger.warning(f"❌ Order blocked: Patient {patient.id} has no wound size")
            return Response(
                {
                    'error': 'Cannot place order',
                    'detail': 'Patient must have wound size (length and width) recorded before placing orders.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ✅ Calculate wound size and max allowed
        wound_length = Decimal(str(patient.wound_size_length))
        wound_width = Decimal(str(patient.wound_size_width))
        wound_area = wound_length * wound_width
        max_allowed_area = wound_area * Decimal('1.2')  # 20% over
        
        logger.info(f"📏 Wound size: {wound_length} x {wound_width} = {wound_area} cm²")
        logger.info(f"📏 Max allowed (120%): {max_allowed_area} cm²")

        # ✅ Validate order items don't exceed max allowed area
        items_data = data.get('items', [])
        if not items_data:
            return Response(
                {'error': 'Order must contain at least one item'},
                status=status.HTTP_400_BAD_REQUEST
            )

        total_ordered_area = Decimal('0')
        from product.models import ProductVariant
        
        for item in items_data:
            variant_id = item.get('variant')
            quantity = item.get('quantity', 0)
            
            try:
                variant = ProductVariant.objects.get(id=variant_id)
                variant_area = parse_variant_size_to_cm2(variant.size)
                
                if variant_area > 0:
                    item_total_area = variant_area * Decimal(str(quantity))
                    total_ordered_area += item_total_area
                    logger.info(f"  📦 Variant {variant_id} ({variant.size}): {variant_area} cm² x {quantity} = {item_total_area} cm²")
                else:
                    logger.warning(f"⚠️ Could not calculate area for variant {variant_id}: {variant.size}")
            except ProductVariant.DoesNotExist:
                return Response(
                    {'error': f'Product variant {variant_id} not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

        logger.info(f"📊 Total ordered area: {total_ordered_area} cm²")
        logger.info(f"📊 Max allowed area: {max_allowed_area} cm²")

        # ✅ Check if order exceeds limit
        if total_ordered_area > max_allowed_area:
            return Response(
                {
                    'error': 'Order exceeds maximum allowed area',
                    'detail': f'Total ordered area ({total_ordered_area} cm²) exceeds maximum allowed ({max_allowed_area} cm²). You can order up to 20% more than the wound size ({wound_area} cm²).',
                    'wound_area': float(wound_area),
                    'max_allowed_area': float(max_allowed_area),
                    'total_ordered_area': float(total_ordered_area)
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create the order
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        order = serializer.instance
        order_verified = data.get('order_verified', False)

        # ✅ ALWAYS save invoice to Azure and send email (removed the condition)
        try:
            self.save_invoice_to_azure(order)
            self.send_invoice_email(order)
            logger.info(f"✅ Invoice saved to Azure and email sent for order {order.id}")
        except Exception as e:
            logger.error(f"❌ Failed to save invoice/send email: {e}", exc_info=True)
            # Continue anyway - order was created successfully

        if order_verified:
            logger.info(f"✅ Order {order.id} created and VERIFIED")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            logger.info(f"✅ Order {order.id} created but PENDING VERIFICATION")
            return Response(
                {
                    "message": "Order placed successfully, but is currently PENDING VERIFICATION.",
                    "order_id": order.id,
                    "order": serializer.data
                },
                status=status.HTTP_201_CREATED
            )

    def save_invoice_to_azure(self, order):
        """Save invoice PDF to Azure Blob Storage."""
        if not AZURE_AVAILABLE:
            logger.warning("⚠️ Azure not available - skipping PDF save")
            return
            
        try:
            html_content = render_to_string('orders/order_invoice.html', {'order': order})
            pdf_file_stream = generate_pdf_from_html(html_content)

            if not pdf_file_stream:
                logger.error(f"❌ Failed to generate PDF for order {order.id}")
                return

            provider_name = clean_string(order.provider.full_name)
            patient_name = clean_string(order.patient.first_name + " " + order.patient.last_name)
            file_name = f"invoice_order_{order.id}.pdf"
            # No "orders/" prefix since we're using the media container
            blob_path = f"orders/{provider_name}/{patient_name}/{file_name}"

            # Get blob service client
            blob_service_client = get_blob_service_client()
            blob_client = blob_service_client.get_blob_client(
                container=settings.AZURE_MEDIA_CONTAINER,
                blob=blob_path
            )

            blob_client.upload_blob(pdf_file_stream, overwrite=True)
            logger.info(f"✅ PDF invoice for order {order.id} saved to Azure at: {blob_path}")

        except Exception as e:
            logger.error(f"❌ Error saving PDF to Azure: {e}", exc_info=True)

    def send_invoice_email(self, order):
        """Send invoice email with PDF attachment."""
        try:
            # Build recipient list safely
            recipient_list = [
                order.provider.email,
                settings.DEFAULT_FROM_EMAIL,
                'harold@promedhealthplus.com',
                'portal@promedhealthplus.com',
                'william.dev@ppromedhealth.com'
            ]
            
            # ✅ Safely add sales rep email if it exists
            if hasattr(order.provider, 'profile') and order.provider.profile:
                if hasattr(order.provider.profile, 'sales_rep') and order.provider.profile.sales_rep:
                    sales_rep_email = order.provider.profile.sales_rep.email
                    if sales_rep_email:
                        recipient_list.insert(1, sales_rep_email)  # Add after provider email
                        logger.info(f"📧 Added sales rep email: {sales_rep_email}")
                else:
                    logger.warning(f"⚠️ No sales rep assigned to provider {order.provider.email}")
            else:
                logger.warning(f"⚠️ No profile found for provider {order.provider.email}")

            subject = f"Invoice for Order {order.id} || {order.patient.first_name} {order.patient.last_name} || {order.created_at.strftime('%Y-%m-%d')}"
            html_content = render_to_string('orders/order_invoice.html', {'order': order})
            pdf_file_stream = generate_pdf_from_html(html_content)

            if not pdf_file_stream:
                EmailMessage(
                    subject=f"{subject} (No PDF Attachment)",
                    body="Please note: We were unable to generate the PDF invoice for this order.",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=recipient_list,
                ).send(fail_silently=False)
                return

            email = EmailMessage(
                subject=subject,
                body="Please find attached the invoice for your recent order.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=recipient_list,
            )
            email.attach(f"invoice_order_{order.id}.pdf", pdf_file_stream.read(), 'application/pdf')
            email.send(fail_silently=False)
            
            logger.info(f"✅ Invoice email sent to {len(recipient_list)} recipients")

        except Exception as e:
            logger.error(f"❌ Error sending invoice email for order {order.id}: {e}")
            raise


class ProviderOrderHistoryView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = api_serializers.PatientOrderHistorySerializer

    def get_queryset(self):
        provider = self.request.user
        return api_models.Patient.objects.filter(
            orders__provider=provider
        ).prefetch_related(
            'orders__items__product',
            'orders__items__variant'
        ).distinct()

    def get_serializer_context(self):
        return {'request': self.request}


class InvoicePDFView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, order_id):
        """Download invoice PDF from Azure Blob Storage."""
        if not AZURE_AVAILABLE:
            raise Http404("Azure storage not available")
            
        try:
            order = api_models.Order.objects.get(id=order_id, provider=request.user)

            provider_name = clean_string(order.provider.full_name)
            patient_name = clean_string(order.patient.first_name + " " + order.patient.last_name)
            file_name = f"invoice_order_{order.id}.pdf"
            blob_path = f"orders/{provider_name}/{patient_name}/{file_name}"

            # Get blob service client
            blob_service_client = get_blob_service_client()
            blob_client = blob_service_client.get_blob_client(
                container=settings.AZURE_MEDIA_CONTAINER,
                blob=blob_path
            )

            stream = blob_client.download_blob()
            return FileResponse(
                stream.readall(),
                as_attachment=True,
                filename=file_name,
                content_type='application/pdf'
            )

        except api_models.Order.DoesNotExist:
            raise Http404("Order not found")
        except Exception as e:
            logger.error(f"❌ Error retrieving invoice PDF: {e}", exc_info=True)
            raise Http404("Could not retrieve invoice")