from fastapi import FastAPI
import random
import time

app = FastAPI()

@app.get("/")
def root():
    return {"status": "healthy"}

@app.get("/stress")
def stress():
    time.sleep(0.5)
    return {"load": random.random()}