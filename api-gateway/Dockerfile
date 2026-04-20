FROM python:3.10-slim

WORKDIR /app

# Prevent Python buffering (important for logs/metrics visibility)
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

COPY . .

RUN pip install --no-cache-dir -r api-gateway/requirements.txt

# 4 workers, reasonable timeout, keepalive tuned
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "api-gateway.main:app", "-w", "4", "-b", "0.0.0.0:8000", "--timeout", "30", "--keep-alive", "5", "--max-requests", "1000", "--max-requests-jitter", "100"]