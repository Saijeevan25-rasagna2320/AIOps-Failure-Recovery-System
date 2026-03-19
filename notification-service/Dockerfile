FROM python:3.10

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r notification-service/requirements.txt

CMD ["uvicorn", "notification-service.main:app", "--host", "0.0.0.0", "--port", "8000"]