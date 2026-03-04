from fastapi import FastAPI, HTTPException
import random
import time
import math

app = FastAPI()

def simulate_delay():
    time.sleep(random.uniform(0, 2))

def simulate_failure():
    if random.random() < 0.05:
        raise HTTPException(status_code=500, detail="User service failure")

def cpu_stress():
    if random.random() < 0.05:
        for i in range(10**6):
            math.sqrt(i)

@app.get("/users/{user_id}")
def get_user(user_id: int):
    simulate_delay()
    simulate_failure()
    cpu_stress()

    return {
        "user_id": user_id,
        "name": "Sample User"
    }

@app.get("/health")
def health():
    return {"status": "user service running"}