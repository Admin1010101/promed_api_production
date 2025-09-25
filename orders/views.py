# orders/views.py
from django.shortcuts import render
from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from django.http import FileResponse, Http404
from django.conf import settings
from django.template.loader import render_to_string
from weasyprint import HTML
from io import BytesIO
from django.core.mail import EmailMessage
import orders.serializers as api_serializers
import orders.models as api_models
from rest_framework.response import Response

# Import Azure BlobServiceClient and clean_string from your utility
from utils.azure_storage import blob_service_client, clean_string
from django.core.files.base import ContentFile

class CreateOrderView(generics.CreateAPIView):
    serializer_class = api_serializers.OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        request.data['provider'] = request.user.id
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        order = serializer.instance
        self.send_invoice_email(order)
        
        # Call the new function to save the PDF to Azure Blob Storage
        self.save_invoice_to_azure(order)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def save_invoice_to_azure(self, order):
        try:
            # Render HTML and generate PDF from the same logic as the email
            html_content = render_to_string('orders/order_invoice.html', {'order': order})
            pdf_file = BytesIO()
            HTML(string=html_content).write_pdf(pdf_file)

            # Define the blob path using a similar logic to your `provider_upload_path`
            provider_name = clean_string(order.provider.full_name)
            patient_name = clean_string(order.patient.first_name + " " + order.patient.last_name)
            file_name = f"invoice_order_{order.id}.pdf"
            blob_path = f"orders/{provider_name}/{patient_name}/{file_name}"

            # Get the blob client
            blob_client = blob_service_client.get_blob_client(
                container=settings.AZURE_CONTAINER,  # Use the container name from settings
                blob=blob_path
            )

            # Upload the PDF to Azure Blob Storage
            pdf_file.seek(0)  # Ensure stream is at beginning
            blob_client.upload_blob(pdf_file, overwrite=True)

            print(f"PDF invoice for order {order.id} saved to Azure Blob at: {blob_path}")

        except Exception as e:
            # Log the error without blocking the main process
            print(f"Error saving PDF to Azure Blob Storage: {e}")


    def send_invoice_email(self, order):
        sales_rep_email = order.provider.profile.sales_rep.email
        recipient_list = [
            order.provider.email,
            sales_rep_email,
            settings.DEFAULT_FROM_EMAIL,
            'william.chandler21@yahoo.com',
            'harold@promedhealthplus.com',
            'kayvoncrenshaw@gmail.com',
            'william.dev@promedhealthplus.com'
        ]
        
        subject = f"Invoice for Order {order.id} || {order.patient.first_name} {order.patient.last_name} || {order.created_at.strftime('%Y-%m-%d')}"
        # Render HTML
        html_content = render_to_string('orders/order_invoice.html', {'order': order})
        # Generate PDF
        pdf_file = BytesIO()
        HTML(string=html_content).write_pdf(pdf_file)
        pdf_file.seek(0)

        # Email with attachment
        email = EmailMessage(
            subject=subject,
            body="Please find attached the invoice for your recent order.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipient_list,
        )
        email.attach(f"invoice_order_{order.id}.pdf", pdf_file.read(), 'application/pdf')
        email.send(fail_silently=False)

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