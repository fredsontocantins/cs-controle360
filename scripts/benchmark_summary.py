import time
import requests
import statistics

BASE_URL = "http://localhost:8000/api"

def benchmark():
    # Warm up
    requests.get(f"{BASE_URL}/summary")
    requests.get(f"{BASE_URL}/summary")

    latencies = []
    for _ in range(50):
        start = time.perf_counter()
        response = requests.get(f"{BASE_URL}/summary")
        end = time.perf_counter()
        if response.status_code == 200:
            latencies.append((end - start) * 1000)
        else:
            print(f"Error: {response.status_code}")

    if latencies:
        print(f"Mean: {statistics.mean(latencies):.2f}ms")
        print(f"Median: {statistics.median(latencies):.2f}ms")
        print(f"Min: {min(latencies):.2f}ms")
        print(f"Max: {max(latencies):.2f}ms")

if __name__ == "__main__":
    benchmark()
