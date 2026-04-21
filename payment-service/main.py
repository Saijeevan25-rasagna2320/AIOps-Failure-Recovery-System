from fastapi import FastAPI, HTTPException
import random, asyncio
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
async def home():
    return {"message": "Payment Service Running"}


# Metrics endpoint
@app.get("/metrics")
async def get_metrics():
    return Response(generate_latest(), media_type="text/plain")


# 🔥 async delay (non-blocking)
async def simulate_delay():
    await asyncio.sleep(random.uniform(0.1, 0.6))  # reduced from 1.5s


# 🔥 controlled failure
def simulate_failure():
    if random.random() < 0.1:   # reduced from 0.25 → 0.1
        raise HTTPException(status_code=500, detail="payment_failed")


# ==============================
# PROCESS PAYMENT
# ==============================
@app.post("/pay")
async def process_payment():
    await simulate_delay()

    simulate_failure()

    return {"status": "success"}