from fastapi import FastAPI
import random
import time

app = FastAPI()

@app.post("/notify")
def notify():

    time.sleep(random.uniform(0,1))

    return {"message": "notification sent"}

@app.get("/health")
def health():
    return {"status": "notification service running"}