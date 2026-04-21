from fastapi import FastAPI
import httpx, time, random, asyncio
from shared.db import db
from fastapi.responses import Response
from prometheus_client import generate_latest

from common.metrics import Metrics
from common.middleware import MetricsMiddleware
from common.retry import retry_request
from common.circuit_breaker import CircuitBreaker

app = FastAPI()
orders = db["orders"]

# Initialize metrics
metrics = Metrics("order")
app.add_middleware(MetricsMiddleware, metrics=metrics)

# Async HTTP client (connection pooling)
client = httpx.AsyncClient(
    timeout=httpx.Timeout(5.0),
    limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
)

# Circuit breakers
user_cb = CircuitBreaker()
inventory_cb = CircuitBreaker()
payment_cb = CircuitBreaker()

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


# 🔥 Safe notification (fire-and-forget)
async def safe_notify():
    try:
        await retry_request(client, "POST", NOTIFICATION_SERVICE)
        metrics.dependency_calls.labels("notification_service", "success").inc()
    except:
        metrics.dependency_calls.labels("notification_service", "failed").inc()
        pass


# ==============================
# MAIN ORDER FLOW
# ==============================
@app.post("/order")
async def place_order(order: dict):
    start = time.time()

    status = "success"
    failure_reason = None

    try:
        # =========================
        # 1. USER + INVENTORY CHECK (PARALLEL)
        # =========================

        if not user_cb.call_allowed():
            raise Exception("user_circuit_open")

        if not inventory_cb.call_allowed():
            raise Exception("inventory_circuit_open")

        async def get_user():
            try:
                res = await retry_request(
                    client, "GET",
                    f"{USER_SERVICE}{order['user_id']}"
                )
                if res.status_code != 200:
                    raise Exception("user_failed")

                user_cb.record_success()
                metrics.dependency_calls.labels("user_service", "success").inc()
                return res

            except:
                user_cb.record_failure()
                metrics.dependency_calls.labels("user_service", "failed").inc()
                raise

        async def check_inventory():
            try:
                res = await retry_request(
                    client, "GET",
                    f"{INVENTORY_SERVICE}/check/{order['product_id']}"
                )
                data = res.json()

                if data.get("status") != "available":
                    raise Exception("out_of_stock")

                inventory_cb.record_success()
                metrics.dependency_calls.labels("inventory_service", "success").inc()
                return data

            except:
                inventory_cb.record_failure()
                metrics.dependency_calls.labels("inventory_service", "failed").inc()
                raise

        # Run both in parallel
        await asyncio.gather(
            get_user(),
            check_inventory()
        )

        # =========================
        # 2. PAYMENT
        # =========================
        if not payment_cb.call_allowed():
            raise Exception("payment_circuit_open")

        try:
            # failure injection
            if random.random() < 0.1:
                raise Exception("simulated_payment_failure")

            pay = await retry_request(client, "POST", PAYMENT_SERVICE)

            if pay.status_code != 200:
                raise Exception("payment_failed")

            payment_cb.record_success()
            metrics.dependency_calls.labels("payment_service", "success").inc()

        except:
            payment_cb.record_failure()
            metrics.dependency_calls.labels("payment_service", "failed").inc()
            raise

        # =========================
        # 3. INVENTORY UPDATE
        # =========================
        try:
            inv = await retry_request(
                client,
                "POST",
                f"{INVENTORY_SERVICE}/decrease/{order['product_id']}"
            )

            if inv.status_code != 200:
                raise Exception("inventory_update_failed")

            metrics.dependency_calls.labels("inventory_update", "success").inc()

        except:
            metrics.dependency_calls.labels("inventory_update", "failed").inc()
            raise

        # =========================
        # 4. NOTIFICATION (ASYNC BACKGROUND)
        # =========================
        asyncio.create_task(safe_notify())

    except Exception as e:
        status = "failed"

        if not failure_reason:
            failure_reason = str(e)

        metrics.error_count.labels(
            endpoint="/order",
            type=failure_reason
        ).inc()

    latency = time.time() - start

    # =========================
    # 5. STORE ORDER
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