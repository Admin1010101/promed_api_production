# orders/views.py
from django.shortcuts import render
from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from django.http import FileResponse, Http404
from django.conf import settings
from django.template.loader import render_to_string
from xhtml2pdf import pisa # ADDED: xhtml2pdf import
from io import BytesIO
from django.core.mail import EmailMessage
import orders.serializers as api_serializers
import orders.models as api_models
from rest_framework.response import Response

# Import Azure BlobServiceClient and clean_string from your utility
from utils.azure_storage import blob_service_client, clean_string
from django.core.files.base import ContentFile

# --- Helper function for PDF generation using xhtml2pdf ---
def generate_pdf_from_html(html_content):
    """Generates a PDF file from HTML content using xhtml2pdf."""
    result_file = BytesIO()

    # Use pisa.pisaDocument to convert HTML to PDF
    # html_content must be encoded to bytes for BytesIO
    pisa_status = pisa.pisaDocument(
        BytesIO(html_content.encode("UTF-8")),
        dest=result_file
    )

    # If there are no errors, return the BytesIO object, otherwise return None
    if not pisa_status.err:
        result_file.seek(0)
        return result_file

    # Log the error if conversion failed
    print(f"xhtml2pdf error encountered: {pisa_status.err}")
    return None

class CreateOrderView(generics.CreateAPIView):
    serializer_class = api_serializers.OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        data['provider'] = request.user.id

        order_verified = data.get('order_verified', False)

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)

        self.perform_create(serializer)

        order = serializer.instance

        if order_verified:
            self.send_invoice_email(order)
            self.save_invoice_to_azure(order)

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(
                {
                    "message": "Order placed successfully, but is currently PENDING VERIFICATION. No invoice was sent.",
                    "order_id": order.id
                },
                status=status.HTTP_201_CREATED
            )

    def save_invoice_to_azure(self, order):
        try:
            # 1. Render HTML
            html_content = render_to_string('orders/order_invoice.html', {'order': order})

            # 2. Generate PDF using xhtml2pdf
            pdf_file_stream = generate_pdf_from_html(html_content)

            if not pdf_file_stream:
                print(f"Skipping Azure upload: Failed to generate PDF for order {order.id}.")
                return

            # Define the blob path
            provider_name = clean_string(order.provider.full_name)
            patient_name = clean_string(order.patient.first_name + " " + order.patient.last_name)
            file_name = f"invoice_order_{order.id}.pdf"
            blob_path = f"orders/{provider_name}/{patient_name}/{file_name}"

            # Get the blob client
            blob_client = blob_service_client.get_blob_client(
                container=settings.AZURE_CONTAINER,
                blob=blob_path
            )

            # Upload the PDF to Azure Blob Storage
            blob_client.upload_blob(pdf_file_stream, overwrite=True)


            print(f"PDF invoice for order {order.id} saved to Azure Blob at: {blob_path}")

        except Exception as e:
            # Log the error without blocking the main process
            print(f"Error saving PDF to Azure Blob Storage: {e}")


    def send_invoice_email(self, order):
        try:
            sales_rep_email = order.provider.profile.sales_rep.email
            recipient_list = [
                order.provider.email,
                sales_rep_email,
                settings.DEFAULT_FROM_EMAIL,
                # 'william.chandler21@yahoo.com',
                'harold@promedhealthplus.com',
                'kayvoncrenshaw@gmail.com',
                'william.dev@promedhealthplus.com'
            ]

            subject = f"Invoice for Order {order.id} || {order.patient.first_name} {order.patient.last_name} || {order.created_at.strftime('%Y-%m-%d')}"

            # 1. Render HTML
            html_content = render_to_string('orders/order_invoice.html', {'order': order})

            # 2. Generate PDF using xhtml2pdf
            pdf_file_stream = generate_pdf_from_html(html_content)

            if not pdf_file_stream:
                # Send email without attachment if PDF generation failed
                EmailMessage(
                    subject=f"{subject} (No PDF Attachment)",
                    body="Please note: We were unable to generate the PDF invoice for this order.",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=recipient_list,
                ).send(fail_silently=False)
                return

            # Email with attachment
            email = EmailMessage(
                subject=subject,
                body="Please find attached the invoice for your recent order.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=recipient_list,
            )
            email.attach(f"invoice_order_{order.id}.pdf", pdf_file_stream.read(), 'application/pdf')
            email.send(fail_silently=False)

        except Exception as e:
            # Log the error if email sending failed
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
        # Pass request context so the serializer can handle ?all=true logic
        return {'request': self.request}


class InvoicePDFView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, order_id):
        # This view retrieves the PDF from Azure, so no generation change is needed here.
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