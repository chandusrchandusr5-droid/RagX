import requests
from pathlib import Path
import time

BASE_URL = "http://127.0.0.1:8000/api"

def test_phase1():
    print("--- 1. Testing Document Upload ---")
    pdf_path = Path(__file__).resolve().parent / "data" / "uploads" / "Attendance_Policy.pdf"
    
    with open(pdf_path, "rb") as f:
        files = {"file": ("Attendance_Policy.pdf", f, "application/pdf")}
        res = requests.post(f"{BASE_URL}/documents/upload", files=files)
        print("Upload Status:", res.status_code)
        print("Upload Response:", res.json())

    print("\n--- 2. Testing Document List ---")
    res = requests.get(f"{BASE_URL}/documents")
    print("List Documents Response:", res.json())

    print("\n--- 3. Testing RAG Query ---")
    question = "What is the minimum attendance requirement?"
    payload = {"question": question, "top_k": 2}
    res = requests.post(f"{BASE_URL}/rag/query", json=payload)
    print("Query Response Status:", res.status_code)
    print("Query Response JSON:")
    import json
    print(json.dumps(res.json(), indent=2))

if __name__ == "__main__":
    time.sleep(2)  # ensure backend ready
    test_phase1()
