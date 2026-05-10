import requests
import time
import logging
import csv
import os

from threading import Lock
from datetime import datetime

PROMETHEUS_URL = "http://prometheus:9090"
POLL_INTERVAL = 5

CSV_FILE = "phase3_aiops/data/raw/metrics_history.csv"

latest_metrics = {}
metrics_lock = Lock()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# -------------------------------------------------
# Advanced Collector Queries
# Schema now matches data.csv:
# timestamp, request_rate, error_rate, latency, cpu, memory
# -------------------------------------------------
queries = {
    "request_rate":
        'sum(rate(order_requests_total[1m])) + '
        'sum(rate(inventory_requests_total[1m])) + '
        'sum(rate(user_requests_total[1m]))',

    "error_rate":
        'sum(rate(order_errors_total[1m])) + '
        'sum(rate(payment_errors_total[1m])) + '
        'sum(rate(api_gateway_errors_total[1m]))',

    "latency":
        'avg(http_request_duration_seconds)',

    "cpu":
        'sum(rate(process_cpu_seconds_total[1m]))',

    "memory":
        'sum(process_resident_memory_bytes)',

    "service_health":
        'count(up == 1)'
}


# -------------------------------------------------
# CSV Init
# -------------------------------------------------
def init_csv():
    os.makedirs(os.path.dirname(CSV_FILE), exist_ok=True)

    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, "w", newline="") as f:
            writer = csv.writer(f)

            writer.writerow([
                "timestamp",
                "request_rate",
                "error_rate",
                "latency",
                "cpu",
                "memory",
                "service_health"
            ])


# -------------------------------------------------
# Save CSV
# -------------------------------------------------
def save_to_csv(row):
    try:
        with open(CSV_FILE, "a", newline="") as f:
            writer = csv.writer(f)

            writer.writerow([
                row["timestamp"],
                row["request_rate"],
                row["error_rate"],
                row["latency"],
                row["cpu"],
                row["memory"],
                row["service_health"]
            ])

    except Exception as e:
        logging.error(
            f"CSV write failed: {e}"
        )


# -------------------------------------------------
# Prometheus Query
# -------------------------------------------------
def fetch_metric(query):
    try:
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": query},
            timeout=4
        )

        response.raise_for_status()

        data = response.json()

        if data["status"] == "success":

            result = data["data"]["result"]

            if result:
                return float(
                    result[0]["value"][1]
                )

    except Exception as e:
        logging.warning(
            f"Metric fetch issue: {e}"
        )

    return 0.0


# -------------------------------------------------
# Collect Metrics
# -------------------------------------------------
def collect_metrics():

    row = {
        "timestamp": datetime.utcnow().isoformat()
    }

    for metric_name, query in queries.items():
        row[metric_name] = fetch_metric(query)

    return row


# -------------------------------------------------
# Main Loop
# -------------------------------------------------
def collect_loop():
    global latest_metrics

    init_csv()

    logging.info(
        "Advanced Collector Started"
    )

    while True:
        try:
            row = collect_metrics()

            with metrics_lock:
                latest_metrics.clear()
                latest_metrics.update(row)

            save_to_csv(row)

            logging.info(
                f"Collected: {row}"
            )

        except Exception as e:
            logging.error(
                f"Collector failure: {e}"
            )

        time.sleep(POLL_INTERVAL)


# -------------------------------------------------
# Thread Safe Getter
# -------------------------------------------------
def get_latest_metrics():
    with metrics_lock:
        return dict(latest_metrics)