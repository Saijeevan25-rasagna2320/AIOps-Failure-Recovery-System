from fastapi import FastAPI, HTTPException
import random
import time
import math
import requests

app = FastAPI()

NOTIFICATION_SERVICE = "http://localhost:8004/notify"

def simulate_delay():
    time.sleep(random.uniform(0, 2))

def simulate_failure():
    if random.random() < 0.05:
        raise HTTPException(status_code=500, detail="Payment failed")

def cpu_stress():
    if random.random() < 0.1:
        for i in range(10**6):
            math.sqrt(i)

@app.post("/pay")
def make_payment():

    simulate_delay()
    simulate_failure()
    cpu_stress()

    try:
        requests.post(NOTIFICATION_SERVICE)
    except:
        pass

    return {"payment": "success"}

@app.get("/health")
def health():
    return {"status": "payment service running"}