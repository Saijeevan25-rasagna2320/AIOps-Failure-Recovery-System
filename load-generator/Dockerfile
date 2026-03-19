FROM python:3.10

WORKDIR /app

COPY . .

RUN pip install fastapi uvicorn requests

CMD ["python", "load-generator/main.py"]