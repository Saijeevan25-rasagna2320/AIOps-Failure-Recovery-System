from fastapi import FastAPI
import requests, time
from shared.db import db

app = FastAPI()
orders = db["orders"]

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