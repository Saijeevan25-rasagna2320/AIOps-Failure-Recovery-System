from fastapi import FastAPI, HTTPException
from shared.db import db
import random, time

app = FastAPI()
inventory = db["inventory"]

@app.get("/check/{product_id}")
def check_stock(product_id: int):
    time.sleep(random.uniform(0.05, 0.4))

    item = inventory.find_one({"product_id": product_id})

    if not item or item["stock"] <= 0:
        return {"status": "out_of_stock"}

    return {"status": "available"}

@app.post("/decrease/{product_id}")
def decrease_stock(product_id: int):
    if random.random() < 0.15:
        raise HTTPException(status_code=500)

    inventory.update_one(
        {"product_id": product_id},
        {"$inc": {"stock": -1}}
    )

    return {"status": "updated"}