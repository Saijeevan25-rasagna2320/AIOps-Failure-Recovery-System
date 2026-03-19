from fastapi import FastAPI
import requests

app = FastAPI()

@app.post("/place-order")
def place(order: dict):
    return requests.post(
        "http://order-service:8000/order",
        json=order
    ).json()