import time
from starlette.middleware.base import BaseHTTPMiddleware

class MetricsMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, metrics):
        super().__init__(app)
        self.metrics = metrics

    async def dispatch(self, request, call_next):
        start_time = time.time()

        try:
            response = await call_next(request)
            self.metrics.request_count.inc()
            return response

        except Exception:
            self.metrics.error_count.inc()
            raise

        finally:
            latency = time.time() - start_time
            self.metrics.latency.observe(latency)