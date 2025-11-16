FROM python:3.11-slim

WORKDIR /app

# Install system deps (if needed for pandas / parquet)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY kafka_consumer_to_minio.py /app/kafka_consumer_to_minio.py

ENV PYTHONUNBUFFERED=1

CMD ["python", "kafka_consumer_to_minio.py"]
