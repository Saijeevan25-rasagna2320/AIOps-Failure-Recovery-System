FROM python:3.10-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

COPY . .

RUN pip install --no-cache-dir -r phase3_aiops/requirements.txt

CMD ["uvicorn", "phase3_aiops.main:app", "--host", "0.0.0.0", "--port", "8010"]