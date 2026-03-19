import requests
import time
import random
import threading
from fastapi import FastAPI
import uvicorn

# ==============================
# CONFIG
# ==============================

URL = "http://api-gateway:8000/place-order"

# Global flag for manual spike
SPIKE_MODE = False

app = FastAPI()


# ==============================
# CONTINUOUS NORMAL TRAFFIC
# ==============================

def normal_load():
    while True:
        order = {
            "user_id": random.randint(1, 10),
            "product_id": random.randint(1, 5)
        }

        try:
            requests.post(URL, json=order, timeout=1)
        except:
            pass

        time.sleep(random.uniform(0.05, 0.2))  # moderate load


# ==============================
# SPIKE TRAFFIC FUNCTION
# ==============================

def spike_worker():
    global SPIKE_MODE

    while True:
        if SPIKE_MODE:
            print("🔥 SPIKE STARTED")

            threads = []

            # burst traffic (parallel)
            for _ in range(50):
                t = threading.Thread(target=burst_requests)
                t.start()
                threads.append(t)

            for t in threads:
                t.join()

            print("⚡ SPIKE COMPLETED")

            SPIKE_MODE = False

        time.sleep(1)


def burst_requests():
    for _ in range(20):  # total ~1000 requests spike
        try:
            requests.post(URL, json={
                "user_id": random.randint(1, 10),
                "product_id": random.randint(1, 5)
            }, timeout=1)
        except:
            pass


# ==============================
# API TO TRIGGER SPIKE
# ==============================

@app.post("/trigger-spike")
def trigger_spike():
    global SPIKE_MODE
    SPIKE_MODE = True
    return {"status": "🔥 spike triggered"}


@app.get("/")
def health():
    return {"status": "load generator running"}


# ==============================
# START EVERYTHING
# ==============================

def start_load():
    # start normal traffic threads
    for _ in range(15):   # increase to 30 for more stress
        t = threading.Thread(target=normal_load)
        t.daemon = True
        t.start()

    # start spike watcher
    threading.Thread(target=spike_worker, daemon=True).start()


if __name__ == "__main__":
    start_load()

    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)