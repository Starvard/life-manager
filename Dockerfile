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
# Make Python a bit lighter and tame malloc fragmentation under low RAM.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MALLOC_ARENA_MAX=2

EXPOSE 8080

# Single worker + a few threads keeps RSS roughly halved vs. 2 workers, which
# matters a lot on Fly's 256 MB shared-cpu-1x. We deliberately do NOT use
# --preload because the APScheduler background thread (push reminders, weekly
# fantasy trade refresh) needs to live inside the request-handling worker.
CMD ["gunicorn", \
     "--bind", "0.0.0.0:8080", \
     "--workers", "1", \
     "--threads", "4", \
     "--max-requests", "500", \
     "--max-requests-jitter", "75", \
     "--timeout", "120", \
     "app:app"]
