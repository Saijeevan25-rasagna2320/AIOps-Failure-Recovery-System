from fastapi import FastAPI
import requests
from fastapi.responses import Response
from prometheus_client import generate_latest

from common.metrics import Metrics
from common.middleware import MetricsMiddleware

app = FastAPI()

# Initialize metrics
metrics = Metrics("api-gateway")

# Add middleware
app.add_middleware(MetricsMiddleware, metrics=metrics)

@app.get("/")
def home():
    return {"message": "Order Service Running"}

# Metrics endpoint (MANDATORY)
@app.get("/metrics")
def get_metrics():
    return Response(generate_latest(), media_type="text/plain")

@app.post("/place-order")
def place(order: dict):
    return requests.post(
        "http://order-service:8000/order",
        json=order
    ).json()