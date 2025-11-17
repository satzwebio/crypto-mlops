# Base image
FROM python:3.10-slim

# Set work directory in container
WORKDIR /app

# Install needed system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*


RUN apt-get update && apt-get install -y bash    

# Copy ONLY Feast repo & jobs (clean and fast)
COPY feast_repo /app/feast_repo

# Install Python dependencies
RUN pip install --no-cache-dir \
    feast[redis,postgres] \
    pandas \
    pyarrow \
    boto3

# Set working directory to actual Feast repo root
WORKDIR /app/feast_repo

# Default entrypoint (overridden by CronJob)
ENTRYPOINT ["/bin/bash"]
