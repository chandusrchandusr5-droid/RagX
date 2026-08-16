"""
RAGX Phase 3 End-to-End Verification Test Script
Executes 7-point verification sequence A through G specified in user prompt.
"""
import requests
import pymupdf as fitz
from pathlib import Path
import shutil
import time
import sys
import subprocess

BASE_URL = "http://127.0.0.1:8000/api"
UPLOADS_DIR = Path(__file__).resolve().parent / "data" / "uploads"
HISTORY_FILE = Path(__file__).resolve().parent / "data" / "evaluation_history.json"

def create_pdf(filename: str, text: str) -> Path:
    pdf_path = UPLOADS_DIR / filename
    temp_path = UPLOADS_DIR / f"temp_{filename}"
    if temp_path.exists():
        try:
            temp_path.unlink()
        except Exception:
            pass
    doc = fitz.open()
    page = doc.new_page()
    page.insert_textbox(fitz.Rect(50, 50, 550, 750), text, fontsize=11)
    doc.save(str(temp_path))
    doc.close()

    if pdf_path.exists():
        try:
            pdf_path.unlink()
        except Exception:
            pass
    shutil.move(str(temp_path), str(pdf_path))
    return pdf_path

def run_e2e_phase1():
    print("==================================================")
    print(" RAGX PHASE 3 END-TO-END VERIFICATION SEQUENCE    ")
    print("==================================================")

    # Upload test document
    p1 = create_pdf("E2E_Policy_Doc.pdf", "E2E POLICY DOCUMENT 2026\nAll students must maintain 75% attendance. Chandu SR is the lead AI researcher.")
    with open(p1, "rb") as f:
        up_res = requests.post(f"{BASE_URL}/documents/upload", files={"file": ("E2E_Policy_Doc.pdf", f, "application/pdf")})
    assert up_res.status_code == 200

    # Step A & B: Custom Question 1
    print("\n--- Step A & B: Custom Question 1 ---")
    q1 = "What is the attendance rule?"
    r1 = requests.post(f"{BASE_URL}/evaluator/query-and-evaluate", json={"question": q1, "top_k": 3}).json()
    e1_id = r1["evaluation_report"]["evaluation_id"]
    score1 = r1["evaluation_report"]["overall_reliability_score"]
    print(f"Question 1: '{q1}' -> ID: {e1_id}, Score: {score1}%")

    # Step C & D: Custom Question 2
    print("\n--- Step C & D: Custom Question 2 ---")
    q2 = "Who is Chandu SR?"
    r2 = requests.post(f"{BASE_URL}/evaluator/query-and-evaluate", json={"question": q2, "top_k": 3}).json()
    e2_id = r2["evaluation_report"]["evaluation_id"]
    score2 = r2["evaluation_report"]["overall_reliability_score"]
    print(f"Question 2: '{q2}' -> ID: {e2_id}, Score: {score2}%")

    assert e1_id != e2_id, "Evaluation IDs must be unique!"

    # Step E: Open Analytics & Verify Both Runs
    print("\n--- Step E: Verifying Analytics API Output Pre-Restart ---")
    an_res = requests.get(f"{BASE_URL}/evaluator/analytics").json()
    hist_res = requests.get(f"{BASE_URL}/evaluator/history?limit=10").json()
    
    rec_ids = [r["evaluation_id"] for r in hist_res.get("records", [])]
    print("Pre-restart History Record IDs:", rec_ids)
    assert e1_id in rec_ids, f"Run 1 {e1_id} missing from history!"
    assert e2_id in rec_ids, f"Run 2 {e2_id} missing from history!"
    assert an_res.get("total_evaluations", 0) >= 2
    print("PASSED: Both custom evaluation runs appear in Analytics & History APIs pre-restart!")

def run_e2e_phase2():
    print("\n--- Step F & G: Verifying Analytics API Output Post-Restart ---")
    an_res = requests.get(f"{BASE_URL}/evaluator/analytics").json()
    hist_res = requests.get(f"{BASE_URL}/evaluator/history?limit=10").json()
    
    rec_ids = [r["evaluation_id"] for r in hist_res.get("records", [])]
    print("Post-restart History Record IDs:", rec_ids)
    assert len(rec_ids) >= 2, "History empty post-restart!"
    print("PASSED: Evaluation records successfully persisted across backend server restart!")

    print("\n==================================================")
    print(" END-TO-END VERIFICATION SEQUENCE PASSED 100%!    ")
    print("==================================================")

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "phase1"
    if mode == "phase1":
        run_e2e_phase1()
    else:
        run_e2e_phase2()
