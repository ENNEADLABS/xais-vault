FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for document processing (PyMuPDF, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --require-hashes -r requirements.txt

COPY packages/ packages/
COPY apps/worker/ apps/worker/

CMD ["python", "-m", "apps.worker.app.main"]
