from fastapi import FastAPI, HTTPException
import httpx
from fastapi.responses import Response
from prometheus_client import generate_latest

from common.metrics import Metrics
from common.middleware import MetricsMiddleware

app = FastAPI()

# Initialize metrics
metrics = Metrics("api-gateway")

# Add middleware
app.add_middleware(MetricsMiddleware, metrics=metrics)

# 🔥 Global async client (connection pooling)
client = httpx.AsyncClient(
    timeout=httpx.Timeout(5.0),
    limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
)


@app.get("/")
async def home():
    return {"message": "API Gateway Running"}


# Metrics endpoint (MANDATORY)
@app.get("/metrics")
async def get_metrics():
    return Response(generate_latest(), media_type="text/plain")


# 🔥 MAIN ENTRY POINT
@app.post("/place-order")
async def place(order: dict):
    try:
        response = await client.post(
            "http://order-service:8000/order",
            json=order
        )

        return response.json()

    except httpx.RequestError as e:
        # network issue
        raise HTTPException(status_code=503, detail="Order service unavailable")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 🔥 Graceful shutdown (VERY IMPORTANT)
@app.on_event("shutdown")
async def shutdown_event():
    await client.aclose()