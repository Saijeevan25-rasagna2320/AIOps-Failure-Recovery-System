from fastapi import FastAPI
import requests, time, random
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

# Metrics endpoint
@app.get("/metrics")
def get_metrics():
    return Response(generate_latest(), media_type="text/plain")


# Service URLs
USER_SERVICE = "http://user-service:8000/users/"
INVENTORY_SERVICE = "http://inventory-service:8000"
PAYMENT_SERVICE = "http://payment-service:8000/pay"
NOTIFICATION_SERVICE = "http://notification-service:8000/notify"


@app.post("/order")
def place_order(order: dict):
    start = time.time()

    status = "success"
    failure_reason = None

    try:
        # 🔹 USER SERVICE
        try:
            res = requests.get(f"{USER_SERVICE}{order['user_id']}", timeout=2)
            if res.status_code != 200:
                metrics.dependency_calls.labels("user_service", "failed").inc()
                raise Exception("user_failed")
            metrics.dependency_calls.labels("user_service", "success").inc()
        except:
            metrics.dependency_calls.labels("user_service", "failed").inc()
            raise

        # 🔹 INVENTORY CHECK
        try:
            stock = requests.get(
                f"{INVENTORY_SERVICE}/check/{order['product_id']}",
                timeout=2
            ).json()

            if stock["status"] != "available":
                metrics.dependency_calls.labels("inventory_service", "failed").inc()
                failure_reason = "out_of_stock"
                raise Exception("out_of_stock")

            metrics.dependency_calls.labels("inventory_service", "success").inc()
        except:
            metrics.dependency_calls.labels("inventory_service", "failed").inc()
            raise

        # 🔹 PAYMENT SERVICE
        try:
            # 🔥 FAILURE INJECTION (for testing dashboards)
            if random.random() < 0.2:
                metrics.dependency_calls.labels("payment_service", "failed").inc()
                raise Exception("simulated_payment_failure")

            pay = requests.post(PAYMENT_SERVICE, timeout=2)

            if pay.status_code != 200:
                metrics.dependency_calls.labels("payment_service", "failed").inc()
                failure_reason = "payment_failed"
                raise Exception("payment_failed")

            metrics.dependency_calls.labels("payment_service", "success").inc()
        except:
            metrics.dependency_calls.labels("payment_service", "failed").inc()
            raise

        # 🔹 INVENTORY UPDATE
        try:
            inv = requests.post(
                f"{INVENTORY_SERVICE}/decrease/{order['product_id']}",
                timeout=2
            )

            if inv.status_code != 200:
                metrics.dependency_calls.labels("inventory_update", "failed").inc()
                failure_reason = "inventory_update_failed"
                raise Exception("inventory_update_failed")

            metrics.dependency_calls.labels("inventory_update", "success").inc()
        except:
            metrics.dependency_calls.labels("inventory_update", "failed").inc()
            raise

        # 🔹 NOTIFICATION
        try:
            notif = requests.post(NOTIFICATION_SERVICE, timeout=2)

            if notif.status_code != 200:
                metrics.dependency_calls.labels("notification_service", "failed").inc()
            else:
                metrics.dependency_calls.labels("notification_service", "success").inc()
        except:
            metrics.dependency_calls.labels("notification_service", "failed").inc()

    except Exception as e:
        status = "failed"

        if not failure_reason:
            failure_reason = str(e)

        # 🔥 ADD THIS (CRITICAL)
        metrics.error_count.labels(
            endpoint="/order",
            type=failure_reason
        ).inc()

    latency = time.time() - start

    # Store in MongoDB (for ML later)
    orders.insert_one({
        "order_id": f"ORD_{int(time.time()*1000)}",
        "user_id": order["user_id"],
        "product_id": order["product_id"],
        "status": status,
        "failure_reason": failure_reason,
        "latency": latency,
        "timestamp": time.time()
    })

    return {
        "status": status,
        "latency": latency,
        "failure_reason": failure_reason
    }