import requests
import pandas as pd
from datetime import datetime, timedelta

# ==============================
# CONFIG
# ==============================

PROM_URL = "http://localhost:9090/api/v1/query_range"

# ⏱️ Change this if needed
HOURS = 3        # collect last 1 hour
STEP = "5s"      # sampling interval

# ==============================
# PROMETHEUS QUERIES
# ==============================

queries = {
    "request_rate": """
    sum(rate(order_requests_total[1m])) +
    sum(rate(inventory_requests_total[1m])) +
    sum(rate(user_requests_total[1m]))
    """,

    "error_rate": """
    sum(rate(order_errors_total[1m])) +
    sum(rate(payment_errors_total[1m])) +
    sum(rate(inventory_errors_total[1m]))
    """,

    # ✅ Stable latency (single service, correct aggregation)
    "latency": """
    histogram_quantile(0.95,
     sum(rate(order_latency_seconds_bucket[1m])) by (le)
    )
    """,

    # ✅ FIXED CPU (aggregate across cores)
    "cpu": """
    avg(rate(node_cpu_seconds_total{mode!="idle"}[1m]))
    """,

    # ✅ Memory usage (not available)
    "memory": """
    node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes
    """
}


# ==============================
# TIME RANGE
# ==============================

end = datetime.utcnow()
start = end - timedelta(hours=HOURS)

params_base = {
    "start": start.isoformat() + "Z",
    "end": end.isoformat() + "Z",
    "step": STEP
}

# ==============================
# DATA COLLECTION
# ==============================

df = None

for name, query in queries.items():
    print(f"📥 Fetching {name}...")

    params = params_base.copy()
    params["query"] = query

    response = requests.get(PROM_URL, params=params).json()

    if response["status"] != "success":
        print(f"❌ Failed to fetch {name}")
        continue

    results = response["data"]["result"]

    if not results:
        print(f"⚠️ No data for {name}")
        continue

    values = results[0]["values"]

    temp_df = pd.DataFrame(values, columns=["timestamp", name])
    temp_df["timestamp"] = pd.to_datetime(temp_df["timestamp"], unit="s")
    temp_df[name] = temp_df[name].astype(float)

    # ==============================
    # 🔥 FIX: OUTER MERGE (no data loss)
    # ==============================
    if df is None:
        df = temp_df
    else:
        df = df.merge(temp_df, on="timestamp", how="outer")

# ==============================
# CLEANING
# ==============================

print("🧹 Cleaning data...")

df = df.sort_values("timestamp")

# Forward fill missing values
df = df.fillna(method="ffill")

# Drop any remaining NaNs (initial rows)
df = df.dropna()

# ==============================
# SAVE DATA
# ==============================

df.to_csv("data.csv", index=False)

print("✅ data.csv created successfully!")
print(f"📊 Total rows: {len(df)}")