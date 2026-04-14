from fastapi import FastAPI, HTTPException
from shared.db import db
import random, time
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
def home():
    return {"message": "Order Service Running"}

# Metrics endpoint (MANDATORY)
@app.get("/metrics")
def get_metrics():
    return Response(generate_latest(), media_type="text/plain")


def simulate_delay():
    time.sleep(random.uniform(0.05, 0.3))

def simulate_failure():
    if random.random() < 0.1:
        raise HTTPException(status_code=500)

@app.post("/users")
def create_user(user: dict):
    simulate_delay()
    users.insert_one(user)
    return {"status": "created"}

@app.get("/users/{user_id}")
def get_user(user_id: int):
    simulate_delay()
    simulate_failure()

    user = users.find_one({"user_id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404)

    return user