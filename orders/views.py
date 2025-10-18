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
from utils.azure_storage import blob_service_client, clean_string
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

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
        if patient.ivrStatus != 'Approved':
            logger.warning(f"❌ Order blocked: Patient {patient.id} IVR status is '{patient.ivrStatus}'")
            return Response(
                {
                    'error': 'Cannot place order',
                    'detail': f'Patient must have IVR status "Approved" to place orders. Current status: {patient.ivrStatus or "Pending"}'
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
                # Parse size like "2 x 2" or "4x4"
                size_str = variant.size
                import re
                match = re.match(r'(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)', size_str, re.IGNORECASE)
                if match:
                    length = Decimal(match.group(1))
                    width = Decimal(match.group(2))
                    variant_area = length * width
                    total_ordered_area += variant_area * Decimal(str(quantity))
                    logger.info(f"  📦 Variant {variant_id} ({size_str}): {variant_area} cm² x {quantity} = {variant_area * Decimal(str(quantity))} cm²")
                else:
                    logger.warning(f"⚠️ Could not parse size for variant {variant_id}: {size_str}")
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

        order_verified = data.get('order_verified', False)

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        order = serializer.instance

        if order_verified:
            self.send_invoice_email(order)
            self.save_invoice_to_azure(order)

            logger.info(f"✅ Order {order.id} created and invoice sent")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            logger.info(f"✅ Order {order.id} created but PENDING VERIFICATION")
            return Response(
                {
                    "message": "Order placed successfully, but is currently PENDING VERIFICATION. No invoice was sent.",
                    "order_id": order.id
                },
                status=status.HTTP_201_CREATED
            )

    def save_invoice_to_azure(self, order):
        try:
            html_content = render_to_string('orders/order_invoice.html', {'order': order})
            pdf_file_stream = generate_pdf_from_html(html_content)

            if not pdf_file_stream:
                print(f"Skipping Azure upload: Failed to generate PDF for order {order.id}.")
                return

            provider_name = clean_string(order.provider.full_name)
            patient_name = clean_string(order.patient.first_name + " " + order.patient.last_name)
            file_name = f"invoice_order_{order.id}.pdf"
            blob_path = f"orders/{provider_name}/{patient_name}/{file_name}"

            blob_client = blob_service_client.get_blob_client(
                container=settings.AZURE_CONTAINER,
                blob=blob_path
            )

            blob_client.upload_blob(pdf_file_stream, overwrite=True)
            print(f"PDF invoice for order {order.id} saved to Azure Blob at: {blob_path}")

        except Exception as e:
            print(f"Error saving PDF to Azure Blob Storage: {e}")

    def send_invoice_email(self, order):
        try:
            sales_rep_email = order.provider.profile.sales_rep.email
            recipient_list = [
                order.provider.email,
                sales_rep_email,
                settings.DEFAULT_FROM_EMAIL,
                'harold@promedhealthplus.com',
                'kayvoncrenshaw@gmail.com',
                'william.dev@promedhealthplus.com'
            ]

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

        except Exception as e:
            print(f"Error sending invoice email for order {order.id}: {e}")
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
        try:
            order = api_models.Order.objects.get(id=order_id, provider=request.user)

            provider_name = clean_string(order.provider.full_name)
            patient_name = clean_string(order.patient.first_name + " " + order.patient.last_name)
            file_name = f"invoice_order_{order.id}.pdf"
            blob_path = f"orders/{provider_name}/{patient_name}/{file_name}"

            blob_client = blob_service_client.get_blob_client(
                container=settings.AZURE_CONTAINER,
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
            print(f"Error retrieving invoice PDF: {e}")
            raise Http404("Could not retrieve invoice")