# orders/views.py
from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from django.http import FileResponse, Http404
from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from xhtml2pdf import pisa
from io import BytesIO
from azure.storage.blob import BlobServiceClient, ContentSettings
import orders.serializers as api_serializers
import orders.models as api_models
from rest_framework.response import Response
from decimal import Decimal
import re  
import logging

logger = logging.getLogger(__name__)


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
        return result_file.getvalue()  # ← FIXED: Return bytes, not BytesIO
    logger.error(f"xhtml2pdf error: {pisa_status.err}")
    return None


def parse_variant_size_to_cm2(size_str):
    """Parse variant size string and return area in cm²."""
    if not size_str:
        return Decimal('0')
    
    try:
        match = re.match(r'(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*(mm|cm)?', size_str, re.IGNORECASE)
        if not match:
            logger.warning(f"⚠️ Could not parse size: {size_str}")
            return Decimal('0')
        
        length = Decimal(match.group(1))
        width = Decimal(match.group(2))
        unit = match.group(3).lower() if match.group(3) else 'cm'
        
        if unit == 'mm':
            length = length / Decimal('10')
            width = width / Decimal('10')
        
        return length * width
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
        logger.info("="*50)
        
        data = request.data.copy()
        data['provider'] = request.user.id

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

        # Check IVR status
        if patient.ivrStatus != 'Approved':
            logger.warning(f"❌ Order blocked: Patient {patient.id} IVR status is '{patient.ivrStatus}'")
            return Response(
                {
                    'error': 'Cannot place order',
                    'detail': f'Patient must have IVR status "Approved". Current: {patient.ivrStatus or "Pending"}'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check wound size
        if not patient.wound_size_length or not patient.wound_size_width:
            return Response(
                {
                    'error': 'Cannot place order',
                    'detail': 'Patient must have wound size recorded.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Calculate limits
        wound_length = Decimal(str(patient.wound_size_length))
        wound_width = Decimal(str(patient.wound_size_width))
        wound_area = wound_length * wound_width
        max_allowed_area = wound_area * Decimal('1.2')
        
        logger.info(f"📏 Wound: {wound_area} cm² | Max: {max_allowed_area} cm²")

        # Validate items
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
            except ProductVariant.DoesNotExist:
                return Response(
                    {'error': f'Product variant {variant_id} not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

        logger.info(f"📊 Total ordered: {total_ordered_area} cm²")

        if total_ordered_area > max_allowed_area:
            return Response(
                {
                    'error': 'Order exceeds maximum allowed area',
                    'detail': f'Total ({total_ordered_area} cm²) exceeds max ({max_allowed_area} cm²)',
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

        # ✅ Save invoice and send email
        try:
            pdf_bytes = self.save_invoice_to_azure(order)
            if pdf_bytes:
                self.send_invoice_email(order, pdf_bytes)
                logger.info(f"✅ Invoice saved & emailed for order {order.id}")
            else:
                logger.error(f"❌ Failed to generate PDF for order {order.id}")
        except Exception as e:
            logger.error(f"❌ Invoice/email error: {e}", exc_info=True)

        logger.info(f"✅ Order {order.id} created successfully")
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def save_invoice_to_azure(self, order):
        """Save invoice PDF to Azure Blob Storage. Returns PDF bytes."""
        try:
            # Generate PDF
            html_content = render_to_string('orders/order_invoice.html', {'order': order})
            pdf_bytes = generate_pdf_from_html(html_content)

            if not pdf_bytes:
                logger.error(f"❌ PDF generation failed for order {order.id}")
                return None

            # Create blob path
            provider_name = clean_string(order.provider.full_name or order.provider.email.split('@')[0])
            patient_name = clean_string(f"{order.patient.first_name}_{order.patient.last_name}")
            file_name = f"invoice_order_{order.id}.pdf"
            blob_path = f"orders/{provider_name}/{patient_name}/{file_name}"

            logger.info(f"📤 Uploading to Azure: {blob_path}")

            # Upload to Azure
            blob_service_client = BlobServiceClient.from_connection_string(
                settings.AZURE_STORAGE_CONNECTION_STRING
            )
            blob_client = blob_service_client.get_blob_client(
                container=settings.AZURE_MEDIA_CONTAINER,
                blob=blob_path
            )

            blob_client.upload_blob(
                pdf_bytes, 
                overwrite=True,
                content_settings=ContentSettings(content_type='application/pdf')
            )

            # Verify upload
            if blob_client.exists():
                logger.info(f"✅ PDF saved to Azure: {blob_path}")
                return pdf_bytes
            else:
                logger.error(f"❌ Blob verification failed: {blob_path}")
                return None

        except Exception as e:
            logger.error(f"❌ Azure upload error: {e}", exc_info=True)
            return None

    def send_invoice_email(self, order, pdf_bytes):
        """Send invoice email with PDF attachment."""
        try:
            # Build recipient list
            recipient_list = [
                order.provider.email,
                settings.DEFAULT_FROM_EMAIL,
                'harold@promedhealthplus.com',
                'portal@promedhealthplus.com',
                'william.dev@ppromedhealth.com'
            ]
            
            # Add sales rep email if exists
            if hasattr(order.provider, 'profile') and order.provider.profile:
                if hasattr(order.provider.profile, 'sales_rep') and order.provider.profile.sales_rep:
                    sales_rep_email = order.provider.profile.sales_rep.email
                    if sales_rep_email:
                        recipient_list.insert(1, sales_rep_email)
                        logger.info(f"📧 Added sales rep: {sales_rep_email}")

            subject = f"Invoice for Order {order.id} || {order.patient.first_name} {order.patient.last_name} || {order.created_at.strftime('%Y-%m-%d')}"

            email = EmailMessage(
                subject=subject,
                body="Please find attached the invoice for your recent order.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=recipient_list,
            )
            
            # Attach PDF
            email.attach(
                f"invoice_order_{order.id}.pdf", 
                pdf_bytes,  # Use the bytes we already generated
                'application/pdf'
            )
            
            email.send(fail_silently=False)
            
            logger.info(f"✅ Email sent to {len(recipient_list)} recipients")

        except Exception as e:
            logger.error(f"❌ Email error for order {order.id}: {e}", exc_info=True)
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
        try:
            order = api_models.Order.objects.get(id=order_id, provider=request.user)

            provider_name = clean_string(order.provider.full_name or order.provider.email.split('@')[0])
            patient_name = clean_string(f"{order.patient.first_name}_{order.patient.last_name}")
            file_name = f"invoice_order_{order.id}.pdf"
            blob_path = f"orders/{provider_name}/{patient_name}/{file_name}"

            logger.info(f"📥 Downloading from Azure: {blob_path}")

            # Get blob from Azure
            blob_service_client = BlobServiceClient.from_connection_string(
                settings.AZURE_STORAGE_CONNECTION_STRING
            )
            blob_client = blob_service_client.get_blob_client(
                container=settings.AZURE_MEDIA_CONTAINER,
                blob=blob_path
            )

            # Check if blob exists
            if not blob_client.exists():
                logger.error(f"❌ Blob not found: {blob_path}")
                raise Http404("Invoice PDF not found in storage")

            # Download blob
            stream = blob_client.download_blob()
            pdf_data = stream.readall()

            logger.info(f"✅ PDF downloaded: {len(pdf_data)} bytes")

            return FileResponse(
                BytesIO(pdf_data),
                as_attachment=True,
                filename=file_name,
                content_type='application/pdf'
            )

        except api_models.Order.DoesNotExist:
            logger.error(f"❌ Order {order_id} not found for user {request.user.email}")
            raise Http404("Order not found")
        except Exception as e:
            logger.error(f"❌ Error retrieving invoice: {e}", exc_info=True)
            raise Http404(f"Could not retrieve invoice: {str(e)}")