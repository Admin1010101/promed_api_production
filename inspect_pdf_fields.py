from pdfrw import PdfReader
import os

# Absolute path to your PDF file
pdf_path = 'media/pdf_templates/promed_healthcare_plus_ivr_blank.pdf'


# Use PdfReader to load the actual PDF file
pdf = PdfReader(pdf_path)

print(f"📄 Inspecting fields in: {pdf_path}\n")

# Iterate through pages and print form field names
for page_num, page in enumerate(pdf.pages, start=1):
    annotations = page.get('/Annots')
    if annotations:
        print(f"--- Page {page_num} ---")
        for annot in annotations:
            if annot.get('/Subtype') == '/Widget':
                field = annot.get('/T')
                if field:
                    print(f"Field: {field}")
