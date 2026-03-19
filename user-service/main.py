from fastapi import FastAPI, HTTPException
from shared.db import db
import random, time

app = FastAPI()
users = db["users"]

def simulate_delay():
    time.sleep(random.uniform(0.05, 0.3))

def simulate_failure():
    if random.random() < 0.1:
        raise HTTPException(status_code=500)

@app.post("/users")
def create_user(user: dict):
    simulate_delay()
    users.insert_one(user)
    return {"status": "created"}

@app.get("/users/{user_id}")
def get_user(user_id: int):
    simulate_delay()
    simulate_failure()

    user = users.find_one({"user_id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404)

    return user