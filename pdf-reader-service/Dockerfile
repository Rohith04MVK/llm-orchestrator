FROM python:3.9-slim

WORKDIR /app
COPY read_pdf.py .

RUN pip install --no-cache-dir PyPDF2
CMD ["python", "read_pdf.py"]