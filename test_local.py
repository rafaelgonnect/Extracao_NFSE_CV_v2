import requests
import json

url = "http://127.0.0.1:8005/analyze-contract-file"
payload = {
    "local_filename": "10144331007.pdf",
    "bank": "itau"
}
headers = {"Content-Type": "application/json"}

try:
    # Test Health
    health = requests.get("http://127.0.0.1:8005/health")
    print(f"Health Status: {health.status_code}")
    print(f"Health Response: {health.text[:200]}") # Truncate

    # Test Contract Analysis
    response = requests.post(url, json=payload)
    print(f"Contract Status: {response.status_code}")
    print(f"Contract Response: {response.text[:200]}")

    # Test Existing Endpoint
    extract = requests.get("http://127.0.0.1:8005/extract")
    print(f"Extract Status: {extract.status_code}")
except Exception as e:
    print(f"Error: {e}")
