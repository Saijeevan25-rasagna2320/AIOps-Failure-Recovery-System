FROM python:3.10

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r inventory-service/requirements.txt

CMD ["uvicorn", "inventory-service.main:app", "--host", "0.0.0.0", "--port", "8000"]