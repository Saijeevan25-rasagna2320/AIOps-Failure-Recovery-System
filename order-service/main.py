from fastapi import FastAPI
import httpx, time, random, asyncio
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

# 🔥 Global async HTTP client (connection pooling)
client = httpx.AsyncClient(
    timeout=httpx.Timeout(5.0),
    limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
)

# Service URLs
USER_SERVICE = "http://user-service:8000/users/"
INVENTORY_SERVICE = "http://inventory-service:8000"
PAYMENT_SERVICE = "http://payment-service:8000/pay"
NOTIFICATION_SERVICE = "http://notification-service:8000/notify"


@app.get("/")
async def home():
    return {"message": "Order Service Running"}


@app.get("/metrics")
async def get_metrics():
    return Response(generate_latest(), media_type="text/plain")


# 🔥 MAIN ORDER FLOW (ASYNC)
@app.post("/order")
async def place_order(order: dict):
    start = time.time()

    status = "success"
    failure_reason = None

    try:
        # =========================
        # 1. USER + INVENTORY CHECK (PARALLEL)
        # =========================
        user_task = client.get(
            f"{USER_SERVICE}{order['user_id']}"
        )

        inventory_task = client.get(
            f"{INVENTORY_SERVICE}/check/{order['product_id']}"
        )

        user_res, stock_res = await asyncio.gather(
            user_task, inventory_task
        )

        # USER VALIDATION
        if user_res.status_code != 200:
            metrics.dependency_calls.labels("user_service", "failed").inc()
            raise Exception("user_failed")

        metrics.dependency_calls.labels("user_service", "success").inc()

        # INVENTORY CHECK
        stock = stock_res.json()

        if stock.get("status") != "available":
            metrics.dependency_calls.labels("inventory_service", "failed").inc()
            failure_reason = "out_of_stock"
            raise Exception("out_of_stock")

        metrics.dependency_calls.labels("inventory_service", "success").inc()

        # =========================
        # 2. PAYMENT
        # =========================
        try:
            # 🔥 failure injection
            if random.random() < 0.2:
                metrics.dependency_calls.labels("payment_service", "failed").inc()
                raise Exception("simulated_payment_failure")

            pay = await client.post(PAYMENT_SERVICE)

            if pay.status_code != 200:
                metrics.dependency_calls.labels("payment_service", "failed").inc()
                failure_reason = "payment_failed"
                raise Exception("payment_failed")

            metrics.dependency_calls.labels("payment_service", "success").inc()

        except:
            metrics.dependency_calls.labels("payment_service", "failed").inc()
            raise

        # =========================
        # 3. INVENTORY UPDATE
        # =========================
        try:
            inv = await client.post(
                f"{INVENTORY_SERVICE}/decrease/{order['product_id']}"
            )

            if inv.status_code != 200:
                metrics.dependency_calls.labels("inventory_update", "failed").inc()
                failure_reason = "inventory_update_failed"
                raise Exception("inventory_update_failed")

            metrics.dependency_calls.labels("inventory_update", "success").inc()

        except:
            metrics.dependency_calls.labels("inventory_update", "failed").inc()
            raise

        # =========================
        # 4. NOTIFICATION (NON-BLOCKING FIRE-AND-FORGET)
        # =========================
        asyncio.create_task(
            client.post(NOTIFICATION_SERVICE)
        )

    except Exception as e:
        status = "failed"

        if not failure_reason:
            failure_reason = str(e)

        # error metric
        metrics.error_count.labels(
            endpoint="/order",
            type=failure_reason
        ).inc()

    latency = time.time() - start

    # =========================
    # 5. DB WRITE (still sync, acceptable for now)
    # =========================
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


# 🔥 graceful shutdown
@app.on_event("shutdown")
async def shutdown_event():
    await client.aclose()