from fastapi import FastAPI, HTTPException
from shared.db import db
import random, asyncio
from fastapi.responses import Response
from prometheus_client import generate_latest

from common.metrics import Metrics
from common.middleware import MetricsMiddleware

app = FastAPI()
inventory = db["inventory"]

# Initialize metrics
metrics = Metrics("inventory")

# Add middleware
app.add_middleware(MetricsMiddleware, metrics=metrics)


@app.get("/")
async def home():
    return {"message": "Inventory Service Running"}


# Metrics endpoint
@app.get("/metrics")
async def get_metrics():
    return Response(generate_latest(), media_type="text/plain")


# 🔥 async delay (non-blocking)
async def simulate_delay():
    await asyncio.sleep(random.uniform(0.05, 0.2))  # reduced + async


# 🔥 controlled failure (reduced)
def simulate_failure():
    if random.random() < 0.05:   # reduced from 0.15 → 0.05
        raise HTTPException(status_code=500, detail="inventory_failure")


# ==============================
# CHECK STOCK
# ==============================
@app.get("/check/{product_id}")
async def check_stock(product_id: int):
    await simulate_delay()

    item = inventory.find_one({"product_id": product_id})

    if item is None:
        return {"status": "not_found", "product_id": product_id}

    if item.get("stock", 0) <= 0:
        return {"status": "out_of_stock"}

    return {"status": "available"}


# ==============================
# DECREASE STOCK
# ==============================
@app.post("/decrease/{product_id}")
async def decrease_stock(product_id: int):
    await simulate_delay()

    # controlled failure
    simulate_failure()

    # atomic update
    result = inventory.update_one(
        {"product_id": product_id, "stock": {"$gt": 0}},
        {"$inc": {"stock": -1}}
    )

    if result.modified_count == 0:
        return {"status": "failed", "reason": "out_of_stock"}

    return {"status": "updated"}