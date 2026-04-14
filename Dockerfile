FROM python:3.11-slim

WORKDIR /app

# Install system deps for reportlab/pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libjpeg62-turbo-dev zlib1g-dev libfreetype6-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Data directory — mounted as persistent volume in production
# Falls back to local ./data if no volume is mounted
ENV LM_DATA_DIR=/data
ENV LM_PORT=8080

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "120", "app:app"]
