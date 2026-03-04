import requests
import threading
import time

URL = "http://localhost:8003/orders"

def send_requests():
    while True:
        try:
            r = requests.post(URL)
            print("Status:", r.status_code)
        except Exception as e:
            print("Request failed", e)

threads = []

for i in range(20):   # number of concurrent users
    t = threading.Thread(target=send_requests)
    t.start()
    threads.append(t)

for t in threads:
    t.join()