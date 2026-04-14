from fastapi import FastAPI, HTTPException
from shared.db import db
import random, time
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
def home():
    return {"message": "Inventory Service Running"}   # ✅ fixed

# Metrics endpoint
@app.get("/metrics")
def get_metrics():
    return Response(generate_latest(), media_type="text/plain")


@app.get("/check/{product_id}")
def check_stock(product_id: int):
    time.sleep(random.uniform(0.05, 0.4))

    item = inventory.find_one({"product_id": product_id})  # ✅ FIXED

    if item is None:
        return {"error": "product_not_found", "product_id": product_id}

    if item.get("stock", 0) <= 0:
        return {"status": "out_of_stock"}

    return {"status": "available"}


@app.post("/decrease/{product_id}")
def decrease_stock(product_id: int):
    print(product_id)
    if random.random() < 0.15:
        raise HTTPException(status_code=500)

    # ✅ atomic update (better)
    result = inventory.update_one(
        {"product_id": product_id, "stock": {"$gt": 0}},
        {"$inc": {"stock": -1}}
    )

    if result.modified_count == 0:
        return {"status": "failed", "reason": "out_of_stock"}

    return {"status": "updated"}