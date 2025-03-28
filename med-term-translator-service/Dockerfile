FROM python:3.9-slim

WORKDIR /app
COPY simplify_terms.py .

RUN pip install --no-cache-dir google-generativeai
CMD ["python", "simplify_terms.py"]