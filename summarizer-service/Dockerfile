FROM python:3.9-slim
WORKDIR /app
COPY summarize.py .
RUN pip install --no-cache-dir google-generativeai dotenv
CMD ["python", "summarize.py"]