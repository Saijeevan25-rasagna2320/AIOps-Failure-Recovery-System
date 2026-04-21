from fastapi import FastAPI
import asyncio, random
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
async def home():
    return {"message": "Notification Service Running"}


# Metrics endpoint
@app.get("/metrics")
async def get_metrics():
    return Response(generate_latest(), media_type="text/plain")


# 🔥 async delay (very light)
async def simulate_delay():
    await asyncio.sleep(random.uniform(0.05, 0.2))  # reduced delay


# ==============================
# SEND NOTIFICATION
# ==============================
@app.post("/notify")
async def notify():
    await simulate_delay()

    # always success (notifications should not break system)
    return {"status": "sent"}