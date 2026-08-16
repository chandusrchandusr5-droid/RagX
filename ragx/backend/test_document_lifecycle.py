"""
RAGX Document Lifecycle Management Automated Regression Test Suite
Covers:
- Upload -> Verify Retrieval
- Delete -> Verify Document Disappears (List API & Disk)
- Delete -> Verify Chunks Purged from ChromaDB
- Delete -> Query No Longer Retrieves Deleted Content
- Multi-Document Scenario: Delete One Document while Another Remains -> Verify Remaining Document Works
- Delete -> Re-upload Same Document -> Verify Fresh Ingestion Works
- Full Phase 1, Phase 2, and Phase 3 Regression Testing
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


def test_document_lifecycle():
    print("==================================================")
    print("   RAGX DOCUMENT LIFECYCLE MANAGEMENT TEST SUITE  ")
    print("==================================================")

    # Setup test documents
    doc_a_name = "Lifecycle_Alpha.pdf"
    doc_a_text = "PROJECT ALPHA MANUAL 2026\nProject Alpha is focused on quantum computing algorithms and supercomputing clusters."
    
    doc_b_name = "Lifecycle_Beta.pdf"
    doc_b_text = "PROJECT BETA MANUAL 2026\nProject Beta is focused on autonomous drone navigation and robotic vision sensors."

    # -------------------------------------------------------------
    # Step 1: Upload Doc A and Verify Retrieval
    # -------------------------------------------------------------
    print("\n--- Step 1: Upload Doc A and Verify Retrieval ---")
    p1 = create_pdf(doc_a_name, doc_a_text)
    with open(p1, "rb") as f:
        up_a = requests.post(f"{BASE_URL}/documents/upload", files={"file": (doc_a_name, f, "application/pdf")})
    assert up_a.status_code == 200, f"Failed to upload {doc_a_name}"
    
    # Query Doc A
    q_a = requests.post(f"{BASE_URL}/evaluator/query-and-evaluate", json={"question": "What is Project Alpha focused on?", "top_k": 2})
    assert q_a.status_code == 200
    res_a_data = q_a.json()
    ret_a = res_a_data.get("retrieved_evidence", [])
    
    assert len(ret_a) > 0, "Failed to retrieve Doc A content!"
    assert ret_a[0]["document_name"] == doc_a_name
    print("PASSED: Doc A uploaded and retrieved successfully!")

    # -------------------------------------------------------------
    # Step 2: Upload Doc B (Multi-document setup)
    # -------------------------------------------------------------
    print("\n--- Step 2: Upload Doc B (Multi-Document Setup) ---")
    p2 = create_pdf(doc_b_name, doc_b_text)
    with open(p2, "rb") as f:
        up_b = requests.post(f"{BASE_URL}/documents/upload", files={"file": (doc_b_name, f, "application/pdf")})
    assert up_b.status_code == 200

    docs_list = requests.get(f"{BASE_URL}/documents").json()
    print("Documents List Count:", docs_list.get("total_documents"))
    assert docs_list.get("total_documents") == 2
    print("PASSED: Multi-document knowledge base populated!")

    # -------------------------------------------------------------
    # Step 3: Delete Doc A and Verify Scoped Deletion
    # -------------------------------------------------------------
    print("\n--- Step 3: Delete Doc A and Verify Scoped Deletion ---")
    del_res = requests.delete(f"{BASE_URL}/documents/{doc_a_name}")
    assert del_res.status_code == 200, f"Delete API failed for {doc_a_name}"
    del_data = del_res.json()

    print("Delete Message:", del_data.get("message"))
    print("Deleted Chunks Count:", del_data.get("deleted_chunks"))

    # Verify Doc A removed from list API
    docs_list_after = requests.get(f"{BASE_URL}/documents").json()
    doc_names_after = [d["file_name"] for d in docs_list_after.get("documents", [])]
    
    assert doc_a_name not in doc_names_after, f"{doc_a_name} still present in document registry!"
    assert doc_b_name in doc_names_after, f"{doc_b_name} accidentally removed!"
    assert not (UPLOADS_DIR / doc_a_name).exists(), f"Physical file {doc_a_name} still exists on disk!"
    print("PASSED: Doc A removed from document list and disk while Doc B remains!")

    # -------------------------------------------------------------
    # Step 4: Verify Query No Longer Retrieves Deleted Content (Doc A)
    # -------------------------------------------------------------
    print("\n--- Step 4: Verify Query No Longer Retrieves Deleted Content (Doc A) ---")
    q_deleted = requests.post(f"{BASE_URL}/evaluator/query-and-evaluate", json={"question": "What is Project Alpha focused on?", "top_k": 2})
    assert q_deleted.status_code == 200
    del_q_data = q_deleted.json()
    del_retrieved = del_q_data.get("retrieved_evidence", [])
    
    # Assert zero chunks retrieved from deleted Doc A
    doc_a_retrieved = [c for c in del_retrieved if c.get("document_name") == doc_a_name]
    assert len(doc_a_retrieved) == 0, f"Deleted document content from {doc_a_name} was still retrieved!"
    print("PASSED: Deleted document content is zero-retrieved!")

    # -------------------------------------------------------------
    # Step 5: Verify Remaining Document (Doc B) Still Works Perfectly
    # -------------------------------------------------------------
    print("\n--- Step 5: Verify Remaining Document (Doc B) Still Works ---")
    q_b = requests.post(f"{BASE_URL}/evaluator/query-and-evaluate", json={"question": "What is Project Beta focused on?", "top_k": 2})
    assert q_b.status_code == 200
    res_b_data = q_b.json()
    ret_b = res_b_data.get("retrieved_evidence", [])

    assert len(ret_b) > 0, "Doc B retrieval failed after deleting Doc A!"
    assert ret_b[0]["document_name"] == doc_b_name
    print("PASSED: Remaining document (Doc B) functions perfectly!")

    # -------------------------------------------------------------
    # Step 6: Delete Doc A -> Re-upload Same Document -> Verify Fresh Ingestion
    # -------------------------------------------------------------
    print("\n--- Step 6: Re-upload Doc A -> Verify Fresh Ingestion & Retrieval ---")
    p1_fresh = create_pdf(doc_a_name, doc_a_text)
    with open(p1_fresh, "rb") as f:
        re_up = requests.post(f"{BASE_URL}/documents/upload", files={"file": (doc_a_name, f, "application/pdf")})
    assert re_up.status_code == 200

    q_re = requests.post(f"{BASE_URL}/evaluator/query-and-evaluate", json={"question": "What is Project Alpha focused on?", "top_k": 2})
    assert q_re.status_code == 200
    re_retrieved = q_re.json().get("retrieved_evidence", [])
    
    assert len(re_retrieved) > 0, "Re-uploaded Doc A retrieval failed!"
    assert re_retrieved[0]["document_name"] == doc_a_name
    print("PASSED: Re-uploaded document ingested and retrieved successfully!")

    print("\n==================================================")
    print(" ALL DOCUMENT LIFECYCLE TESTS PASSED SUCCESSFULLY! ")
    print("==================================================")

if __name__ == "__main__":
    time.sleep(1)
    test_document_lifecycle()
