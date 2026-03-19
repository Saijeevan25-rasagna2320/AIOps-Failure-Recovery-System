from fastapi import FastAPI, HTTPException
import random, time

app = FastAPI()

@app.post("/pay")
def process_payment():
    time.sleep(random.uniform(0.1, 1.5))

    if random.random() < 0.25:
        raise HTTPException(status_code=500)

    return {"status": "success"}