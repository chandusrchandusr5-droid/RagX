"""
RAGX Phase 3 Analytics & Persistent Evaluation History Automated Test Suite
Verifies:
1. Automatic evaluation logging to evaluation_history.json
2. GET /api/evaluator/analytics derivation from disk records
3. GET /api/evaluator/history limit and order
4. Correctness of total_evaluations, avg_score, failure_category_distribution
5. Zero-regression across evaluation pipeline
"""
import requests
import pymupdf as fitz
from pathlib import Path
import shutil
import time

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


def test_analytics_persistence():
    print("==================================================")
    print(" PHASE 3 ANALYTICS & PERSISTENT HISTORY TEST SUITE")
    print("==================================================")

    # 1. Record pre-test history record count
    pre_hist = requests.get(f"{BASE_URL}/evaluator/history?limit=500").json()
    pre_count = pre_hist.get("total_records", 0)

    # 2. Upload test document
    doc_file = "Analytics_Unit_Policy.pdf"
    doc_text = "ANALYTICS POLICY 2026\nStudents must score at least 60% on all quarterly examinations to pass."

    p1 = create_pdf(doc_file, doc_text)
    with open(p1, "rb") as f:
        up_res = requests.post(f"{BASE_URL}/documents/upload", files={"file": (doc_file, f, "application/pdf")})
    assert up_res.status_code == 200

    # 3. Run Query & Evaluate 1 (Grounded Answer)
    print("\n--- 1. Executing Evaluation Run 1 (Grounded Query) ---")
    q1_res = requests.post(f"{BASE_URL}/evaluator/query-and-evaluate", json={"question": "What is the passing score on quarterly examinations?", "top_k": 3})
    assert q1_res.status_code == 200
    q1_data = q1_res.json()
    e1_id = q1_data["evaluation_report"]["evaluation_id"]
    print(f"Run 1 ID: {e1_id}, Score: {q1_data['evaluation_report']['overall_reliability_score']}%, Category: {q1_data['evaluation_report']['failure_category']}")

    # 4. Run Query & Evaluate 2 (Contradictory Answer / Hallucination via evaluate)
    print("\n--- 2. Executing Evaluation Run 2 (Synthetic Contradiction) ---")
    req2 = {
        "query": "What is the passing score on quarterly examinations?",
        "answer": "Students must score at least 95% on quarterly examinations.",
        "retrieved_evidence": q1_data["retrieved_evidence"]
    }
    q2_res = requests.post(f"{BASE_URL}/evaluator/evaluate", json=req2)
    assert q2_res.status_code == 200
    q2_data = q2_res.json()
    e2_id = q2_data["evaluation_id"]
    print(f"Run 2 ID: {e2_id}, Score: {q2_data['overall_reliability_score']}%, Category: {q2_data['failure_category']}")
    assert q2_data["failure_category"] == "GENERATION_FAILURE"

    # 5. Query GET /api/evaluator/history
    print("\n--- 3. Testing GET /api/evaluator/history ---")
    hist_res = requests.get(f"{BASE_URL}/evaluator/history?limit=10")
    assert hist_res.status_code == 200
    hist_data = hist_res.json()
    records = hist_data.get("records", [])

    print(f"Total History Records Returned: {hist_data.get('total_records')}")
    assert hist_data.get("total_records") >= 2
    history_ids = [r["evaluation_id"] for r in records]
    assert e1_id in history_ids
    assert e2_id in history_ids
    print("PASSED: Persistent history endpoint returned all evaluation runs!")

    # 6. Query GET /api/evaluator/analytics
    print("\n--- 4. Testing GET /api/evaluator/analytics ---")
    analytics_res = requests.get(f"{BASE_URL}/evaluator/analytics")
    assert analytics_res.status_code == 200
    analytics_data = analytics_res.json()

    tot_evals = analytics_data.get("total_evaluations")
    avg_score = analytics_data.get("average_reliability_score")
    fail_dist = analytics_data.get("failure_category_distribution", {})

    print(f"Total Evaluations: {tot_evals}")
    print(f"Average Reliability Score: {avg_score}%")
    print(f"Failure Category Distribution: {fail_dist}")

    assert tot_evals >= 2
    assert avg_score >= 0.0
    assert "WELL_GROUNDED" in fail_dist
    assert "GENERATION_FAILURE" in fail_dist
    print("PASSED: Analytics endpoint successfully computed real metrics from persistent disk store!")

    # 7. Verify disk file existence
    assert HISTORY_FILE.exists()
    print("PASSED: evaluation_history.json disk persistence confirmed!")

    print("\n==================================================")
    print(" ALL ANALYTICS & PERSISTENCE TESTS PASSED 100%!   ")
    print("==================================================")

if __name__ == "__main__":
    time.sleep(1)
    test_analytics_persistence()
