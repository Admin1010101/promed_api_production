import logging
from io import BytesIO
from datetime import datetime
from xhtml2pdf import pisa
from django.template.loader import render_to_string # We'll still use this for the shell

logger = logging.getLogger(__name__)

def generate_baa_pdf(user, baa_data):
    """
    Generates a PDF for the signed BAA agreement, mimicking the React form's structure.
    
    Args:
        user: The authenticated User object.
        baa_data: Dictionary of validated form data (snake_case keys from serializer).
    
    Returns:
        BytesIO object containing the PDF content.
    """
    
    # Map snake_case keys back to camelCase for display, matching frontend
    display_data = {
        'effectiveDate': baa_data.get('effective_date', 'N/A'),
        'providerCompanyName': baa_data.get('provider_company_name', 'N/A'),
        'monthlyVolume': baa_data.get('monthly_volume', 'N/A'),
        'signatoryName': baa_data.get('signatory_name', 'N/A'),
        'signatoryTitle': baa_data.get('signatory_title', 'N/A'),
        'signature': baa_data.get('signature', 'N/A'),
        'signatureDate': baa_data.get('signature_date', 'N/A'),
    }

    # Prepare context for the HTML template, including dynamic form data
    context = {
        'user': user,
        'form_data': display_data, # This is the data we'll inject into the template
        'signed_date': datetime.now().strftime('%B %d, %Y at %I:%M %p'),
        'year': datetime.now().year,
    }
    
    # Render an HTML template that includes the BAA text and the form input values.
    # This template (e.g., 'provider_auth/baa_full_document.html') will reconstruct 
    # the look of your React components.
    html_string = render_to_string('provider_auth/baa_full_document.html', context)
    
    pdf_buffer = BytesIO()
    pisa_status = pisa.CreatePDF(
        html_string,
        dest=pdf_buffer,
        encoding='utf-8'
    )
    
    if pisa_status.err:
        logger.error(f"PDF generation error for BAA for {user.email}: {pisa_status.err}")
        raise Exception("Failed to generate BAA PDF") 
    
    pdf_buffer.seek(0)
    return pdf_buffer