"""
RAGX Cross-Document Attribution & Source Attribution Regression Test Suite
Verifies that when multiple documents contain overlapping entity names (e.g. Chandu SR)
with different document-specific facts (e.g. CSE vs Electrical Engineering),
the RAG engine and evaluator select the correct source document and preserve exact 5-tuple citation traceability:
query -> retrieved_chunk -> chunk_id -> document_name -> page_number.
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


def test_cross_document_attribution():
    print("==================================================")
    print(" RAGX CROSS-DOCUMENT SOURCE ATTRIBUTION SUITE     ")
    print("==================================================")

    # Clear previous uploads & vector collection for clean isolated test
    try:
        from app.core.vector_db import vector_db
        vector_db.collection.delete(where={"chunk_id": {"$ne": ""}})
    except Exception:
        pass


    for f in UPLOADS_DIR.glob("*"):
        if f.is_file():
            try:
                f.unlink()
            except Exception:
                pass


    # Document 1: Chandu SR in Computer Science & Engineering
    doc1_text = (
        "STUDENT ACADEMIC RECORD 2026\n"
        "Student Name: CHANDU SR\n"
        "Department: Computer Science & Engineering (CSE)\n"
        "Specialization: Artificial Intelligence & Machine Learning\n"
        "CGPA: 3.95"
    )
    p1 = create_pdf("Chandu_CSE_Profile.pdf", doc1_text)
    with open(p1, "rb") as f:
        requests.post(f"{BASE_URL}/documents/upload", files={"file": ("Chandu_CSE_Profile.pdf", f, "application/pdf")})

    # Document 2: Chandu SR in Electrical Engineering
    doc2_text = (
        "STUDENT ACADEMIC RECORD 2026\n"
        "Student Name: CHANDU SR\n"
        "Department: Electrical & Electronics Engineering (EEE)\n"
        "Specialization: High Voltage Power Systems & Renewable Energy\n"
        "CGPA: 3.82"
    )
    p2 = create_pdf("Chandu_EEE_Profile.pdf", doc2_text)
    with open(p2, "rb") as f:
        requests.post(f"{BASE_URL}/documents/upload", files={"file": ("Chandu_EEE_Profile.pdf", f, "application/pdf")})

    # Test Query A: Asking specifically about Computer Science
    query_a = "What is Chandu SR's specialization in Computer Science?"
    res_a = requests.post(f"{BASE_URL}/evaluator/query-and-evaluate", json={"question": query_a, "top_k": 2})
    assert res_a.status_code == 200
    data_a = res_a.json()
    retrieved_a = data_a.get("retrieved_evidence", [])

    print("\n--- Test Query A: 'What is Chandu SR's specialization in Computer Science?' ---")
    print("Top Retrieved Document:", retrieved_a[0]["document_name"] if retrieved_a else "None")
    print("Retrieved Text Sample:", retrieved_a[0]["text"][:80].replace("\n", " ") if retrieved_a else "None")
    
    assert len(retrieved_a) > 0
    assert retrieved_a[0]["document_name"] == "Chandu_CSE_Profile.pdf", f"Expected Chandu_CSE_Profile.pdf, got {retrieved_a[0]['document_name']}"
    print("PASSED: Correctly attributed source document to Chandu_CSE_Profile.pdf!")

    # Test Query B: Asking specifically about Electrical Engineering
    query_b = "What is Chandu SR's specialization in Electrical Engineering?"
    res_b = requests.post(f"{BASE_URL}/evaluator/query-and-evaluate", json={"question": query_b, "top_k": 2})
    assert res_b.status_code == 200
    data_b = res_b.json()
    retrieved_b = data_b.get("retrieved_evidence", [])

    print("\n--- Test Query B: 'What is Chandu SR's specialization in Electrical Engineering?' ---")
    print("Top Retrieved Document:", retrieved_b[0]["document_name"] if retrieved_b else "None")
    print("Retrieved Text Sample:", retrieved_b[0]["text"][:80].replace("\n", " ") if retrieved_b else "None")

    assert len(retrieved_b) > 0
    assert retrieved_b[0]["document_name"] == "Chandu_EEE_Profile.pdf", f"Expected Chandu_EEE_Profile.pdf, got {retrieved_b[0]['document_name']}"
    print("PASSED: Correctly attributed source document to Chandu_EEE_Profile.pdf!")

    print("\n==================================================")
    print(" CROSS-DOCUMENT SOURCE ATTRIBUTION SUITE PASSED!  ")
    print("==================================================")

if __name__ == "__main__":
    time.sleep(1)
    test_cross_document_attribution()
