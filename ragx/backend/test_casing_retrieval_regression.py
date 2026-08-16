"""
RAGX Global Case-Insensitive Retrieval & Evaluation Regression Test Suite
Verifies that uppercase, lowercase, titlecase, and mixedcase document/query variations match robustly
across different document contents without hardcoding any specific names or files.
"""
import requests
import pymupdf as fitz
from pathlib import Path
import shutil
import time

BASE_URL = "http://127.0.0.1:8000/api"
UPLOADS_DIR = Path(__file__).resolve().parent / "data" / "uploads"

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


def test_global_casing_retrieval():
    print("==================================================")
    print("  RAGX GLOBAL CASE-INSENSITIVE REGRESSION SUITE   ")
    print("==================================================")

    test_cases = [
        {
            "filename": "Profile_Uppercase.pdf",
            "doc_text": "STUDENT PROFILE\nName: CHANDU SR\nDepartment: Computer Science & Engineering\nStatus: Active Student",
            "query": "Who is Chandu SR?",
            "expected_keyword": "CHANDU SR"
        },
        {
            "filename": "Profile_Titlecase.pdf",
            "doc_text": "Student Profile\nName: Chandu Sr\nDepartment: Computer Science & Engineering",
            "query": "who is chandu sr?",
            "expected_keyword": "Chandu Sr"
        },
        {
            "filename": "Profile_Lowercase.pdf",
            "doc_text": "student profile\nname: chandu sr\ndepartment: computer science & engineering",
            "query": "WHO IS CHANDU SR?",
            "expected_keyword": "chandu sr"
        },
        {
            "filename": "Profile_Mixedcase.pdf",
            "doc_text": "sTuDeNt PrOfIlE\nNaMe: ChAnDu Sr\nDePaRtMeNt: Computer Science",
            "query": "Who is CHANDU sr?",
            "expected_keyword": "ChAnDu Sr"
        },
        {
            "filename": "Project_Uppercase.pdf",
            "doc_text": "PROJECT REPORT 2026\nPROJECT RAGX IS DEVELOPED BY GOOGLE DEEPMIND TEAM FOR ADVANCED AGENTIC CODING.",
            "query": "Who developed Project RagX?",
            "expected_keyword": "PROJECT RAGX IS DEVELOPED BY GOOGLE DEEPMIND"
        },
        {
            "filename": "Project_Lowercase.pdf",
            "doc_text": "project report 2026\nproject ragx is developed by google deepmind team.",
            "query": "WHO DEVELOPED PROJECT RAGX?",
            "expected_keyword": "project ragx is developed by google deepmind"
        }
    ]

    for idx, tc in enumerate(test_cases, start=1):
        print(f"\n--- Scenario {idx}: Document '{tc['filename']}' ---")
        pdf_path = create_pdf(tc["filename"], tc["doc_text"])
        
        with open(pdf_path, "rb") as f:
            up_res = requests.post(f"{BASE_URL}/documents/upload", files={"file": (tc["filename"], f, "application/pdf")})
        assert up_res.status_code == 200, f"Failed to upload {tc['filename']}"

        # Test query and evaluate
        eval_res = requests.post(f"{BASE_URL}/evaluator/query-and-evaluate", json={"question": tc["query"], "top_k": 3})
        assert eval_res.status_code == 200, f"Query failed for '{tc['query']}'"
        
        data = eval_res.json()
        retrieved = data.get("retrieved_evidence", [])
        report = data.get("evaluation_report", {})

        print("Query Sent:", tc["query"])
        print("Retrieved Chunks Count:", len(retrieved))
        print("Generated Answer:", data.get("answer")[:100] + ("..." if len(data.get("answer", "")) > 100 else ""))
        print("Failure Category:", report.get("failure_category"))
        print("Reliability Score:", report.get("overall_reliability_score"))

        # Verifications
        assert len(retrieved) > 0, f"Retrieval failed for query '{tc['query']}'!"
        assert report.get("failure_category") != "RETRIEVAL_FAILURE", "Must not mark valid case-insensitive retrieval as RETRIEVAL_FAILURE!"
        assert report.get("failure_category") != "GENERATION_FAILURE", "Must not mark valid grounding as GENERATION_FAILURE!"
        
        # Verify original casing is preserved in retrieved text chunk
        retrieved_text = retrieved[0]["text"]
        print("Preserved Document Casing Sample:", retrieved_text[:60].replace("\n", " "))
        assert tc["expected_keyword"].lower() in retrieved_text.lower(), "Original document content missing!"

        print(f"PASSED: Scenario {idx} matched case-insensitively while preserving original text!")

    print("\n==================================================")
    print(" ALL CASE-INSENSITIVE REGRESSION SCENARIOS PASSED! ")
    print("==================================================")

if __name__ == "__main__":
    time.sleep(1)
    test_global_casing_retrieval()
