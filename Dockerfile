# Use a smaller base image
FROM python:3.10-slim

# Install only necessary dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
COPY .env ./
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py daily-quote.py sa-key.json ./

ENTRYPOINT ["python", "daily-quote.py"]