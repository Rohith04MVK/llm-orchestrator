FROM python:3.9-slim

WORKDIR /app
COPY anonymize_text.py .

RUN pip install --no-cache-dir google-generativeai
CMD ["python", "anonymize_text.py"]