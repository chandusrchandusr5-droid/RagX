"""
RAGX Phase 3 — Automated Test Suite for Answer Reliability Evaluation & Hallucination Detection
Covers all 11 explicit test scenarios specified in the approved plan.
"""
import requests
from pathlib import Path
import time
import json
import shutil
import pymupdf as fitz

BASE_URL = "http://127.0.0.1:8000/api"
UPLOADS_DIR = Path(__file__).resolve().parent / "data" / "uploads"
CHROMA_DIR = Path(__file__).resolve().parent / "data" / "chroma_db"

def create_pdf(filename: str, pages_text: list[str]) -> Path:
    pdf_path = UPLOADS_DIR / filename
    temp_path = UPLOADS_DIR / f"temp_{filename}"
    if temp_path.exists():
        try:
            temp_path.unlink()
        except Exception:
            pass
    doc = fitz.open()
    for text in pages_text:
        page = doc.new_page()
        if text:
            page.insert_textbox(fitz.Rect(50, 50, 550, 750), text, fontsize=10)
    doc.save(str(temp_path))
    doc.close()
    
    if pdf_path.exists():
        try:
            pdf_path.unlink()
        except Exception:
            pass
    shutil.move(str(temp_path), str(pdf_path))
    return pdf_path


def test_phase3():
    print("==================================================")
    print("      RAGX PHASE 3 AUTOMATED TEST SUITE          ")
    print("==================================================")

    # -------------------------------------------------------------
    # TEST 1: Empty Evidence -> NOT_EVALUABLE / EVIDENCE_INSUFFICIENCY
    # -------------------------------------------------------------
    print("\n--- 1. Testing Empty Evidence Context ---")
    req1 = {
        "query": "What is the minimum attendance requirement?",
        "answer": "The minimum attendance requirement is 75%.",
        "retrieved_evidence": []
    }
    res1 = requests.post(f"{BASE_URL}/evaluator/evaluate", json=req1)
    assert res1.status_code == 200, f"Expected 200 OK, got {res1.status_code}"
    rep1 = res1.json()

    print("Status:", rep1.get("evaluation_status"))
    print("Category:", rep1.get("failure_category"))
    print("Score:", rep1.get("overall_reliability_score"))

    assert rep1.get("evaluation_status") in ["NOT_EVALUABLE", "EVALUATED"]
    assert rep1.get("failure_category") in ["EVIDENCE_INSUFFICIENCY", "RETRIEVAL_FAILURE"]
    assert rep1.get("overall_reliability_score") == 0.0
    print("PASSED: Empty evidence context handled safely without division-by-zero errors!")

    # -------------------------------------------------------------
    # TEST 2: Top-K Missing but Full-KB Evidence Exists -> RETRIEVAL_FAILURE
    # -------------------------------------------------------------
    print("\n--- 2. Testing Top-K Missing + Full-KB Evidence Exists (RETRIEVAL_FAILURE) ---")
    p1 = create_pdf("Attendance_Policy.pdf", [
        "COLLEGE OF ENGINEERING & TECHNOLOGY\nACADEMIC POLICY MANUAL — SECTION 4: ATTENDANCE RULES\nAll undergraduate students must maintain a minimum attendance of 75% in every course module."
    ])
    with open(p1, "rb") as f:
        requests.post(f"{BASE_URL}/documents/upload", files={"file": ("Attendance_Policy.pdf", f, "application/pdf")})

    req2 = {
        "query": "What is the minimum attendance requirement?",
        "answer": "The minimum attendance requirement is 75%.",
        "retrieved_evidence": []  # Omitted from Top-K
    }
    res2 = requests.post(f"{BASE_URL}/evaluator/evaluate", json=req2)
    assert res2.status_code == 200
    rep2 = res2.json()

    print("Category (Top-K Missing + KB Evidence Exists):", rep2.get("failure_category"))
    assert rep2.get("failure_category") == "RETRIEVAL_FAILURE"
    print("PASSED: Oracle correctly attributed failure to RETRIEVAL_FAILURE without blaming LLM!")

    # -------------------------------------------------------------
    # TEST 3: Top-K Evidence Present + Contradictory Answer -> GENERATION_FAILURE
    # -------------------------------------------------------------
    print("\n--- 3. Testing Top-K Evidence Present + Contradictory Answer (GENERATION_FAILURE) ---")
    evidence_chunk = {
        "id": "Attendance_Policy.pdf_p1_001",
        "chunk_id": "Attendance_Policy.pdf_p1_001",
        "document_name": "Attendance_Policy.pdf",
        "page_number": 1,
        "text": "All undergraduate students must maintain a minimum attendance of 75% in every course module."
    }
    req3 = {
        "query": "What is the minimum attendance requirement?",
        "answer": "The minimum attendance requirement is 80%.",
        "retrieved_evidence": [evidence_chunk]
    }
    res3 = requests.post(f"{BASE_URL}/evaluator/evaluate", json=req3)
    assert res3.status_code == 200
    rep3 = res3.json()

    print("Category (Contradictory Answer):", rep3.get("failure_category"))
    claim_status = rep3.get("claim_analysis", [{}])[0].get("support_status")
    print("Claim Support Status:", claim_status)

    assert claim_status == "CONTRADICTED"
    assert rep3.get("failure_category") == "GENERATION_FAILURE"
    print("PASSED: Contradiction identified and attributed correctly to GENERATION_FAILURE!")

    # -------------------------------------------------------------
    # TEST 4: Top-K Evidence Present + Unsupported Factual Claim -> GENERATION_FAILURE
    # -------------------------------------------------------------
    print("\n--- 4. Testing Top-K Evidence Present + Unsupported Claim (GENERATION_FAILURE) ---")
    req4 = {
        "query": "What are the grading rules?",
        "answer": "Grade O is awarded for 95% and above with a gold medal.",
        "retrieved_evidence": [evidence_chunk]
    }
    res4 = requests.post(f"{BASE_URL}/evaluator/evaluate", json=req4)
    assert res4.status_code == 200
    rep4 = res4.json()

    print("Category (Unsupported Claim):", rep4.get("failure_category"))
    assert rep4.get("failure_category") == "GENERATION_FAILURE"
    print("PASSED: Unsupported factual claim attributed to GENERATION_FAILURE when Top-K evidence was available!")

    # -------------------------------------------------------------
    # TEST 5: Phase 2 SUSPECTED_CONFLICT_SIGNAL -> Diagnostic Warning
    # -------------------------------------------------------------
    print("\n--- 5. Testing Phase 2 SUSPECTED_CONFLICT_SIGNAL Diagnostic ---")
    p2 = create_pdf("Attendance_Rules_v2.pdf", [
        "COLLEGE OF ENGINEERING & TECHNOLOGY\nREVISED REGULATION 2026\nSECTION 4: ATTENDANCE MANDATE\nAll enrolled undergraduate students must maintain a minimum attendance of 80% in every course module."
    ])
    with open(p2, "rb") as f:
        requests.post(f"{BASE_URL}/documents/upload", files={"file": ("Attendance_Rules_v2.pdf", f, "application/pdf")})

    req5 = {
        "query": "What is the minimum attendance requirement?",
        "answer": "All undergraduate students must maintain a minimum attendance of 75%.",
        "retrieved_evidence": [
            evidence_chunk,
            {
                "id": "Attendance_Rules_v2.pdf_p1_002",
                "chunk_id": "Attendance_Rules_v2.pdf_p1_002",
                "document_name": "Attendance_Rules_v2.pdf",
                "page_number": 1,
                "text": "All enrolled undergraduate students must maintain a minimum attendance of 80% in every course module."
            }
        ]
    }
    res5 = requests.post(f"{BASE_URL}/evaluator/evaluate", json=req5)
    assert res5.status_code == 200
    rep5 = res5.json()

    p2_refs = rep5.get("phase2_cross_references", [])
    print("Phase 2 Cross-References:", [r.get("mapped_category") for r in p2_refs])
    assert any("SUSPECTED_KNOWLEDGE_CONFLICT" in r.get("mapped_category", "") for r in p2_refs), "Expected SUSPECTED_KNOWLEDGE_CONFLICT diagnostic"
    print("PASSED: Phase 2 suspected conflict preserved as diagnostic signal without converting to confirmed conflict!")

    # -------------------------------------------------------------
    # TEST 6: Strict 5-Tuple Citation Traceability
    # -------------------------------------------------------------
    print("\n--- 6. Testing 5-Tuple Citation Traceability ---")
    claims_analysis = rep3.get("claim_analysis", [])
    assert len(claims_analysis) > 0
    matched_ev = claims_analysis[0].get("matched_evidence", {})

    print("5-Tuple Evidence Mapping:", matched_ev)
    assert "source_file" in matched_ev
    assert "page_number" in matched_ev
    assert "chunk_id" in matched_ev
    assert "evidence_snippet" in matched_ev
    assert "similarity_score" in matched_ev
    print("PASSED: 5-tuple citation traceability verified (claim -> chunk -> chunk_id -> doc -> page)!")

    # -------------------------------------------------------------
    # TEST 7: Deterministic Decision Hierarchy & Preservation of Both Levels
    # -------------------------------------------------------------
    print("\n--- 7. Testing Preservation of Both Claim-Level Status & Overall Category ---")
    assert "claim_analysis" in rep3
    assert "failure_category" in rep3
    assert "reliability_status" in rep3
    assert "overall_reliability_score" in rep3
    print("PASSED: Both claim-level statuses and overall evaluation category preserved in report!")

    # -------------------------------------------------------------
    # TEST 8: Deterministic Repeated Evaluation
    # -------------------------------------------------------------
    print("\n--- 8. Testing Deterministic Repeated Evaluation ---")
    res_repeat1 = requests.post(f"{BASE_URL}/evaluator/evaluate", json=req3).json()
    res_repeat2 = requests.post(f"{BASE_URL}/evaluator/evaluate", json=req3).json()

    assert res_repeat1["overall_reliability_score"] == res_repeat2["overall_reliability_score"]
    assert res_repeat1["failure_category"] == res_repeat2["failure_category"]
    print("PASSED: Repeated evaluation on identical input produced 100% deterministic output!")

    # -------------------------------------------------------------
    # TEST 9: POST /api/rag/query-and-evaluate Combined Endpoint
    # -------------------------------------------------------------
    print("\n--- 9. Testing POST /api/rag/query-and-evaluate ---")
    combined_res = requests.post(f"{BASE_URL}/evaluator/query-and-evaluate", json={"question": "What is the minimum attendance requirement?", "top_k": 2})
    assert combined_res.status_code == 200, "Combined query and evaluate endpoint failed!"
    combined_json = combined_res.json()

    print("Combined Answer:", combined_json.get("answer")[:80] + "...")
    assert "evaluation_report" in combined_json
    print("PASSED: Combined RAG query and evaluation endpoint functioning perfectly!")

    # -------------------------------------------------------------
    # TEST 10: Phase 1 RAG Regression Test
    # -------------------------------------------------------------
    print("\n--- 10. Phase 1 RAG Regression Test ---")
    p1_res = requests.post(f"{BASE_URL}/rag/query", json={"question": "What is the minimum attendance requirement?", "top_k": 2})
    assert p1_res.status_code == 200
    assert "answer" in p1_res.json()
    print("PASSED: Phase 1 RAG query endpoint functions perfectly without regression!")

    # -------------------------------------------------------------
    # TEST 11: Phase 2 Quality Audit Regression Test
    # -------------------------------------------------------------
    print("\n--- 11. Phase 2 Data Quality Audit Regression Test ---")
    p2_res = requests.get(f"{BASE_URL}/quality/audit")
    assert p2_res.status_code == 200
    assert "composite_reliability_score" in p2_res.json()
    print("PASSED: Phase 2 Data Quality Audit endpoint functions perfectly without regression!")

    print("\n==================================================")
    print("    ALL PHASE 3 AUTOMATED TESTS PASSED (11/11)    ")
    print("==================================================")

if __name__ == "__main__":
    time.sleep(1)
    test_phase3()
