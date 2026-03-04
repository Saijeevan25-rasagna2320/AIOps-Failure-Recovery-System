from fastapi import FastAPI, HTTPException
import requests
import random
import time
import math

app = FastAPI()

USER_SERVICE = "http://localhost:8001/users/1"
PAYMENT_SERVICE = "http://localhost:8002/pay"

def simulate_delay():
    time.sleep(random.uniform(0,2))

def simulate_failure():
    if random.random() < 0.05:
        raise HTTPException(status_code=500, detail="Order processing failure")

def cpu_stress():
    if random.random() < 0.05:
        for i in range(10**6):
            math.sqrt(i)

@app.post("/orders")
def create_order():

    simulate_delay()
    simulate_failure()
    cpu_stress()

    try:
        user = requests.get(USER_SERVICE, timeout=2).json()
    except:
        raise HTTPException(status_code=500, detail="User service unavailable")

    try:
        payment = requests.post(PAYMENT_SERVICE, timeout=2).json()
    except:
        raise HTTPException(status_code=500, detail="Payment service unavailable")

    return {
        "order": "created",
        "user": user,
        "payment": payment
    }

@app.get("/health")
def health():
    return {"status": "order service running"}