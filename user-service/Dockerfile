FROM python:3.10

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r user-service/requirements.txt

CMD ["uvicorn", "user-service.main:app", "--host", "0.0.0.0", "--port", "8000"]