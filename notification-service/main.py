from fastapi import FastAPI
import time, random

from fastapi.responses import Response
from prometheus_client import generate_latest

from common.metrics import Metrics
from common.middleware import MetricsMiddleware

app = FastAPI()

# Initialize metrics
metrics = Metrics("notification")

# Add middleware
app.add_middleware(MetricsMiddleware, metrics=metrics)

@app.get("/")
def home():
    return {"message": "Order Service Running"}

# Metrics endpoint (MANDATORY)
@app.get("/metrics")
def get_metrics():
    return Response(generate_latest(), media_type="text/plain")

@app.post("/notify")
def notify():
    time.sleep(random.uniform(0.2, 1))
    return {"status": "sent"}