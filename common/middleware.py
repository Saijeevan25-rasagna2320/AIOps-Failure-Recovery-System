import time
from starlette.middleware.base import BaseHTTPMiddleware

class MetricsMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, metrics):
        super().__init__(app)
        self.metrics = metrics

    async def dispatch(self, request, call_next):
        # 🚫 Skip metrics endpoint
        if request.url.path == "/metrics":
            return await call_next(request)

        start_time = time.time()

        endpoint = request.url.path
        method = request.method

        # 🔥 Track in-progress requests (advanced)
        self.metrics.in_progress.labels(endpoint=endpoint).inc()

        try:
            response = await call_next(request)

            status_code = str(response.status_code)

            # ✅ Request count
            self.metrics.request_count.labels(
                method=method,
                endpoint=endpoint,
                status=status_code
            ).inc()

            # 🔥 Treat 5xx as errors automatically
            if status_code.startswith("5"):
                self.metrics.error_count.labels(
                    endpoint,
                    "server_error"
                ).inc()

            return response

        except Exception:
            # ❗ Exception-based errors
            self.metrics.error_count.labels(
                endpoint,
                "exception"
            ).inc()
            raise

        finally:
            # ⏱ Latency
            latency = time.time() - start_time
            self.metrics.latency.labels(endpoint=endpoint).observe(latency)

            # 🔥 Decrement in-progress
            self.metrics.in_progress.labels(endpoint=endpoint).dec()