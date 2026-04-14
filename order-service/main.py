from fastapi import FastAPI
import requests, time
from shared.db import db
from fastapi.responses import Response
from prometheus_client import generate_latest

from common.metrics import Metrics
from common.middleware import MetricsMiddleware

app = FastAPI()
orders = db["orders"]

# Initialize metrics
metrics = Metrics("order")

# Add middleware
app.add_middleware(MetricsMiddleware, metrics=metrics)

@app.get("/")
def home():
    return {"message": "Order Service Running"}

# Metrics endpoint (MANDATORY)
@app.get("/metrics")
def get_metrics():
    return Response(generate_latest(), media_type="text/plain")



USER_SERVICE = "http://user-service:8000/users/"
INVENTORY_SERVICE = "http://inventory-service:8000"
PAYMENT_SERVICE = "http://payment-service:8000/pay"
NOTIFICATION_SERVICE = "http://notification-service:8000/notify"

@app.post("/order")
def place_order(order: dict):
    start = time.time()

    try:
        requests.get(f"{USER_SERVICE}{order['user_id']}")
        stock = requests.get(f"{INVENTORY_SERVICE}/check/{order['product_id']}").json()

        if stock["status"] != "available":
            raise Exception()

        requests.post(PAYMENT_SERVICE)
        requests.post(f"{INVENTORY_SERVICE}/decrease/{order['product_id']}")
        requests.post(NOTIFICATION_SERVICE)

        status = "success"

    except:
        status = "failed"

    latency = time.time() - start

    orders.insert_one({
        "user_id": order["user_id"],
        "product_id": order["product_id"],
        "status": status,
        "latency": latency,
        "timestamp": time.time()
    })

    return {"status": status, "latency": latency}