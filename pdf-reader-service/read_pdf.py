import os
import sys
from PyPDF2 import PdfReader
import time

print("PDF Reader Service starting...")

# Expects the PDF file to be mounted as /data/input.pdf
input_pdf_path = '/data/input.pdf'
output_text_path = '/data/output.txt' # Output will be text

try:
    if not os.path.exists(input_pdf_path):
        raise FileNotFoundError(f"Input PDF not found at {input_pdf_path}")

    print(f"Reading PDF: {input_pdf_path}")
    reader = PdfReader(input_pdf_path)
    number_of_pages = len(reader.pages)
    print(f"PDF has {number_of_pages} pages.")

    extracted_text = ""
    for i, page in enumerate(reader.pages):
        print(f"Extracting text from page {i+1}...")
        page_text = page.extract_text()
        if page_text:
            extracted_text += page_text + "\n\n" # Add space between pages
        else:
            print(f"Warning: No text extracted from page {i+1}.")

    # Simulate some work
    time.sleep(1)

    with open(output_text_path, 'w', encoding='utf-8') as f_out:
        f_out.write(extracted_text)

    print(f"PDF Reader Service finished successfully. Extracted ~{len(extracted_text)} characters.")

except Exception as e:
    print(f"PDF Reader Service Error: {e}")
    # Write error to output file for debugging
    try:
        with open(output_text_path, 'w', encoding='utf-8') as f_err:
            f_err.write(f"Error during PDF processing: {e}")
    except Exception as write_err:
         print(f"Additionally, failed to write error to output file: {write_err}")
    sys.exit(1) # Indicate failure