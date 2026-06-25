FROM python:3.12-slim

WORKDIR /app

# Runtime deps only (pandas/openpyxl are dev-time, for data/ingest_rent.py).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY static ./static
COPY data/rent.db ./data/rent.db

# Hugging Face Spaces (and most PaaS) route to $PORT; HF's default is 7860.
ENV PORT=7860
EXPOSE 7860

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
