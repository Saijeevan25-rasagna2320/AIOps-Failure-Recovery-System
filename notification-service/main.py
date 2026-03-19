from fastapi import FastAPI
import time, random

app = FastAPI()

@app.post("/notify")
def notify():
    time.sleep(random.uniform(0.2, 1))
    return {"status": "sent"}