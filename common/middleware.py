import time
from starlette.middleware.base import BaseHTTPMiddleware

class MetricsMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, metrics):
        super().__init__(app)
        self.metrics = metrics

    async def dispatch(self, request, call_next):
        # 🚫 Skip metrics endpoint (avoid noise)
        if request.url.path == "/metrics":
            return await call_next(request)

        start_time = time.time()

        endpoint = request.url.path
        method = request.method

        try:
            response = await call_next(request)

            # ✅ Request count with labels
            self.metrics.request_count.labels(
                method=method,
                endpoint=endpoint,
                status=str(response.status_code)
            ).inc()

            return response

        except Exception:
            # ❗ Error tracking
            self.metrics.error_count.labels(
                endpoint=endpoint
            ).inc()
            raise

        finally:
            # ⏱ Latency tracking
            latency = time.time() - start_time

            self.metrics.latency.labels(
                endpoint=endpoint
            ).observe(latency)