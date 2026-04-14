from fastapi import FastAPI, HTTPException
import random, time
from fastapi.responses import Response
from prometheus_client import generate_latest

from common.metrics import Metrics
from common.middleware import MetricsMiddleware

app = FastAPI()

# Initialize metrics
metrics = Metrics("payment")

# Add middleware
app.add_middleware(MetricsMiddleware, metrics=metrics)

@app.get("/")
def home():
    return {"message": "Order Service Running"}

# Metrics endpoint (MANDATORY)
@app.get("/metrics")
def get_metrics():
    return Response(generate_latest(), media_type="text/plain")

@app.post("/pay")
def process_payment():
    time.sleep(random.uniform(0.1, 1.5))

    if random.random() < 0.25:
        raise HTTPException(status_code=500)

    return {"status": "success"}