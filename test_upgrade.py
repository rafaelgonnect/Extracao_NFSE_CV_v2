import requests
import base64

# Simple PDF header
pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Title (Test) >>\nendobj\ntrailer\n<< /Size 1 >>\n%%EOF"
pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')

url = "http://127.0.0.1:8000/extract"
payload = {
    "pdf_base64": pdf_base64
}

try:
    print("Testing /health...")
    health = requests.get("http://127.0.0.1:8000/health")
    print(f"Health: {health.status_code}")

    print("\nTesting /extract (NFS-e)...")
    response_nfse = requests.post(url, json=payload)
    print(f"Status: {response_nfse.status_code}")

    print("\nTesting /analyze-contract-file (Contract)...")
    payload_contract = {
        "local_filename": "380062.pdf",
        "bank": "itau"
    }
    url_contract = "http://127.0.0.1:8000/analyze-contract-file"
    # Using a known local file name from previous context if possible, or just making sure it handles error
    response_contract = requests.post(url_contract, json=payload_contract)
    print(f"Status: {response_contract.status_code}")
    print(f"Response: {response_contract.text[:500]}")
except Exception as e:
    print(f"Error: {e}")
