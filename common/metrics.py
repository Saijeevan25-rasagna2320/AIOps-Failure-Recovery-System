from prometheus_client import Counter, Histogram

class Metrics:
    def __init__(self, service_name: str):
        self.request_count = Counter(
            f"{service_name}_requests_total",
            "Total number of requests"
        )

        self.error_count = Counter(
            f"{service_name}_errors_total",
            "Total number of failed requests"
        )

        self.latency = Histogram(
            f"{service_name}_latency_seconds",
            "Request latency in seconds",
            buckets=(0.1, 0.3, 0.5, 1, 2, 5, 10)
        )