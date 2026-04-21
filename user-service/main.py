from fastapi import FastAPI, HTTPException
from shared.db import db
import random, asyncio
from fastapi.responses import Response
from prometheus_client import generate_latest

from common.metrics import Metrics
from common.middleware import MetricsMiddleware

app = FastAPI()
users = db["users"]

# Initialize metrics
metrics = Metrics("user")

# Add middleware
app.add_middleware(MetricsMiddleware, metrics=metrics)


@app.get("/")
async def home():
    return {"message": "User Service Running"}


# Metrics endpoint
@app.get("/metrics")
async def get_metrics():
    return Response(generate_latest(), media_type="text/plain")


# 🔥 async delay (non-blocking)
async def simulate_delay():
    await asyncio.sleep(random.uniform(0.05, 0.2))


# 🔥 controlled failure (reduced)
def simulate_failure():
    if random.random() < 0.03:   # 🔥 reduced from 0.1 → 0.03
        raise HTTPException(status_code=500, detail="user_service_failure")


# CREATE USER
@app.post("/users")
async def create_user(user: dict):
    await simulate_delay()

    users.insert_one(user)

    return {"status": "created"}


# GET USER
@app.get("/users/{user_id}")
async def get_user(user_id: int):
    await simulate_delay()

    # controlled failure
    simulate_failure()

    user = users.find_one({"user_id": user_id}, {"_id": 0})

    if not user:
        raise HTTPException(status_code=404, detail="user_not_found")

    return user