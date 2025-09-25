from pdfrw import PdfReader, PdfWriter, PdfDict, PdfString
from io import BytesIO
from azure.storage.blob import BlobServiceClient
from django.conf import settings

# PDF field keys
ANNOT_KEY = '/Annots'
ANNOT_FIELD_KEY = '/T'
ANNOT_VAL_KEY = '/V'
SUBTYPE_KEY = '/Subtype'
WIDGET_SUBTYPE_KEY = '/Widget'

# Map logical form types to Azure blob names
# TEMPLATE_BLOB_NAMES = {
#     'IVR_FORM': 'pdf_templates/promed_healthcare_plus_ivr_blank.pdf',
#     # Add more mappings if needed
# }

TEMPLATE_BLOB_NAMES = {
    'IVR_FORM': 'promed_healthcare_plus_ivr_blank.pdf',
}


def fetch_pdf_template_from_azure(blob_name: str) -> BytesIO:
    """
    Download a PDF template from Azure Blob Storage and return it as a BytesIO stream.
    """
    blob_service_client = BlobServiceClient.from_connection_string(settings.AZURE_CONNECTION_STRING)
    # container_client = blob_service_client.get_container_client(settings.AZURE_CONTAINER)
    container_client = blob_service_client.get_container_client('media')
    blob_client = container_client.get_blob_client(blob_name)

    if not blob_client.exists():
        raise FileNotFoundError(f"Template PDF '{blob_name}' not found in Azure storage.")

    buffer = BytesIO()
    blob_client.download_blob().readinto(buffer)
    buffer.seek(0)
    return buffer

def fill_pdf(template_type: str, data_dict: dict, output_stream: BytesIO):
    """
    Fill a form-fillable PDF (loaded from Azure) with the provided data,
    and write the result to the given output_stream.
    """
    blob_name = TEMPLATE_BLOB_NAMES.get(template_type)
    if not blob_name:
        raise ValueError(f"No template defined for form type '{template_type}'")

    pdf_stream = fetch_pdf_template_from_azure(blob_name)
    pdf = PdfReader(pdf_stream)

    for page in pdf.pages:
        annotations = page.get(ANNOT_KEY)
        if annotations:
            for annotation in annotations:
                if annotation.get(SUBTYPE_KEY) == WIDGET_SUBTYPE_KEY:
                    key = annotation.get(ANNOT_FIELD_KEY)
                    if key:
                        key_name = key.to_unicode().strip('()')
                        if key_name in data_dict:
                            value = data_dict[key_name]
                            annotation.update(
                                PdfDict(V=PdfString.encode(value))
                            )
                            # Force re-render of field value by removing stale appearance
                            if '/AP' in annotation:
                                del annotation['/AP']

    writer = PdfWriter()
    writer.write(output_stream, pdf)
