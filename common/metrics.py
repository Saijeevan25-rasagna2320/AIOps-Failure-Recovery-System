from prometheus_client import Counter, Histogram, Gauge 

class Metrics:
    def __init__(self, service_name: str):
        self.service_name = service_name

        # 🔹 Total requests with labels
        self.request_count = Counter(
            f"{service_name}_requests_total",
            "Total number of requests",
            ["method", "endpoint", "status"]
        )

        # 🔹 Error tracking
        self.error_count = Counter(
            f"{service_name}_errors_total",
            "Total number of errors",
            ["endpoint", "type"]   # ✅ add "type"
        )

        # 🔹 Latency tracking (Histogram for percentiles)
        self.latency = Histogram(
            f"{service_name}_latency_seconds",
            "Request latency in seconds",
            ["endpoint"],
            buckets=(0.1, 0.3, 0.5, 1, 2, 5, 10)
        )

        # 🔥 Dependency tracking (VERY IMPORTANT FOR YOUR PROJECT)
        self.dependency_calls = Counter(
            f"{service_name}_dependency_calls_total",
            "Calls to dependent services",
            ["dependency", "status"]
        )

        self.in_progress = Gauge(
            f"{service_name}_in_progress_requests",
            "Number of in-progress requests",
            ["endpoint"]
        )