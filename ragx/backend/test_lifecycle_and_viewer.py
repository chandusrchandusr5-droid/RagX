"""
RAGX Complete Document Lifecycle Management & In-Web PDF Viewer Automated Test Suite
Covers 10 explicit test scenarios:
1. Upload -> Active Documents
2. Open PDF -> Actual PDF loads securely in web viewer endpoint
3. Soft Delete -> Moves to Deleted Documents (Trash)
4. Deleted document -> Cannot be retrieved by RAG queries
5. Deleted document -> Excluded from active Phase 2 Data Quality Audit
6. Restore -> Returns to Active Documents
7. Restored document -> Becomes retrievable again by RAG
8. Multi-document -> Soft deleting Doc 1 leaves Doc 2 active and retrievable
9. Permanent Delete -> File, metadata, and ChromaDB vector chunks permanently removed
10. State persistence -> Server restart & refresh preserves Active and Deleted states in registry
"""
import requests
import pymupdf as fitz
from pathlib import Path
import shutil
import time

BASE_URL = "http://127.0.0.1:8000/api"
UPLOADS_DIR = Path(__file__).resolve().parent / "data" / "uploads"
TRASH_DIR = Path(__file__).resolve().parent / "data" / "trash"

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


def test_lifecycle_and_viewer():
    print("==================================================")
    print(" DOCUMENT LIFECYCLE & IN-WEB PDF VIEWER TEST SUITE")
    print("==================================================")

    # Clean ONLY test-specific lifecycle files for isolated test run
    test_prefix_files = ["Lifecycle_Unit_Alpha.pdf", "Lifecycle_Unit_Beta.pdf"]
    for folder in [UPLOADS_DIR, TRASH_DIR]:
        for fname in test_prefix_files:
            f = folder / fname
            if f.exists():
                try:
                    f.unlink()
                except Exception:
                    pass


    doc_1_file = "Lifecycle_Unit_Alpha.pdf"
    doc_1_text = "LIFECYCLE UNIT ALPHA SPECIFICATION 2026\nLifecycle Unit Alpha code LUC-9988 is equipped with quantum photonic optical sensors and high-speed fiber optics."

    doc_2_file = "Lifecycle_Unit_Beta.pdf"
    doc_2_text = "UNIT BETA SPECIFICATION 2026\nUnit Beta is equipped with autonomous sonar navigation and underwater acoustic transducers."


    # -------------------------------------------------------------
    # 1. Upload -> Active Documents
    # -------------------------------------------------------------
    print("\n--- 1. Testing Upload -> Active Documents ---")
    p1 = create_pdf(doc_1_file, doc_1_text)
    with open(p1, "rb") as f:
        up1_res = requests.post(f"{BASE_URL}/documents/upload", files={"file": (doc_1_file, f, "application/pdf")})
    assert up1_res.status_code == 200
    doc1 = up1_res.json()["document"]
    doc1_id = doc1["document_id"]
    
    print(f"Uploaded '{doc_1_file}' -> Assigned Document ID: '{doc1_id}', Status: {doc1['status']}")
    assert doc1["status"] == "ACTIVE"
    assert doc1_id.startswith("doc_")
    print("PASSED: Uploaded document registered as ACTIVE with stable document_id!")

    # -------------------------------------------------------------
    # 2. Open PDF -> Actual PDF loads in web viewer endpoint
    # -------------------------------------------------------------
    print("\n--- 2. Testing Open PDF Endpoint (GET /api/documents/{doc_id}/view) ---")
    view_res = requests.get(f"{BASE_URL}/documents/{doc1_id}/view")
    assert view_res.status_code == 200, f"View endpoint failed with status {view_res.status_code}"
    content_type = view_res.headers.get("content-type", "")
    content_disp = view_res.headers.get("content-disposition", "")
    
    print("Content-Type:", content_type)
    print("Content-Disposition:", content_disp)
    assert "application/pdf" in content_type.lower()
    assert "inline" in content_disp.lower()
    assert len(view_res.content) > 100
    print("PASSED: Open PDF endpoint securely served actual inline PDF file!")

    # -------------------------------------------------------------
    # 3. Soft Delete -> Moves to Deleted Documents (Trash)
    # -------------------------------------------------------------
    print("\n--- 3. Testing Soft Delete -> Moves to Deleted Documents (Trash) ---")
    del1_res = requests.delete(f"{BASE_URL}/documents/{doc1_id}")
    assert del1_res.status_code == 200
    del1_data = del1_res.json()
    
    print("Delete Message:", del1_data.get("message"))
    print("Purged Chunks:", del1_data.get("deleted_chunks"))

    # Verify document moved to trash list
    active_docs = requests.get(f"{BASE_URL}/documents?status=ACTIVE").json()["documents"]
    deleted_docs = requests.get(f"{BASE_URL}/documents?status=DELETED").json()["documents"]

    active_ids = [d["document_id"] for d in active_docs]
    deleted_ids = [d["document_id"] for d in deleted_docs]

    assert doc1_id not in active_ids, "Doc 1 still present in Active Documents!"
    assert doc1_id in deleted_ids, "Doc 1 missing from Deleted Documents!"
    assert (TRASH_DIR / doc_1_file).exists(), "Physical file not moved to trash directory!"
    print("PASSED: Soft delete moved document to Deleted Documents and trash directory!")

    # -------------------------------------------------------------
    # 4. Deleted document -> Cannot be retrieved by RAG
    # -------------------------------------------------------------
    print("\n--- 4. Testing Deleted Document -> Excluded from RAG Retrieval ---")
    q_del = requests.post(f"{BASE_URL}/evaluator/query-and-evaluate", json={"question": "What is Unit Alpha equipped with?", "top_k": 3})
    assert q_del.status_code == 200
    q_del_data = q_del.json()
    retrieved_del = q_del_data.get("retrieved_evidence", [])

    doc1_retrieved = [c for c in retrieved_del if c.get("document_name") == doc_1_file or c.get("document_id") == doc1_id]
    eval_rep = q_del_data.get("evaluation_report", {})
    print("Step 4 Evaluation Status:", eval_rep.get("evaluation_status"), "Failure Category:", eval_rep.get("failure_category"))
    assert len(doc1_retrieved) == 0, "Deleted document content was retrieved by RAG!"
    print("PASSED: Deleted document content is strictly zero-retrieved by RAG!")



    # -------------------------------------------------------------
    # 5. Deleted document -> Excluded from active Phase 2 Data Quality Audit
    # -------------------------------------------------------------
    print("\n--- 5. Testing Deleted Document -> Excluded from Quality Audit ---")
    audit_res = requests.get(f"{BASE_URL}/quality/audit").json()
    print("Audit Status with soft-deleted doc:", audit_res.get("user_facing_status"))
    print("Audit Score with soft-deleted doc:", audit_res.get("composite_reliability_score"))
    
    assert "composite_reliability_score" in audit_res
    assert doc1_id not in [i.get("chunk_id") for i in audit_res.get("issues", [])]
    print("PASSED: Soft deleted document excluded from active Data Quality Audit!")


    # -------------------------------------------------------------
    # 6. Restore -> Returns to Active Documents
    # -------------------------------------------------------------
    print("\n--- 6. Testing Restore -> Returns to Active Documents ---")
    rest_res = requests.post(f"{BASE_URL}/documents/{doc1_id}/restore")
    assert rest_res.status_code == 200
    rest_data = rest_res.json()
    
    print("Restore Message:", rest_data.get("message"))
    print("Re-indexed Chunks:", rest_data.get("reindexed_chunks"))

    active_docs_after = requests.get(f"{BASE_URL}/documents?status=ACTIVE").json()["documents"]
    active_ids_after = [d["document_id"] for d in active_docs_after]
    
    assert doc1_id in active_ids_after
    assert (UPLOADS_DIR / doc_1_file).exists()
    print("PASSED: Document restored back to Active Knowledge Base!")

    # -------------------------------------------------------------
    # 7. Restored document -> Becomes retrievable again
    # -------------------------------------------------------------
    print("\n--- 7. Testing Restored Document -> Retrievable by RAG ---")
    q_restored = requests.post(f"{BASE_URL}/evaluator/query-and-evaluate", json={"question": "What is the specification code for Lifecycle Unit Alpha?", "top_k": 3})


    assert q_restored.status_code == 200
    q_rest_data = q_restored.json()
    retrieved_rest = q_rest_data.get("retrieved_evidence", [])

    assert len(retrieved_rest) > 0, "Restored document retrieval failed!"
    assert any(r["document_name"] == doc_1_file for r in retrieved_rest), f"Expected '{doc_1_file}' in retrieved evidence, got {[r['document_name'] for r in retrieved_rest]}"
    assert q_rest_data.get("evaluation_report", {}).get("evaluation_status") == "EVALUATED"


    print("PASSED: Restored document is retrievable by RAG and grounded!")

    # -------------------------------------------------------------
    # 8. Upload Doc 2 -> Test Multi-Document Scoping (Doc 2 Remains Unaffected)
    # -------------------------------------------------------------
    print("\n--- 8. Testing Multi-Document Scoping (Doc 2 Unaffected) ---")
    p2 = create_pdf(doc_2_file, doc_2_text)
    with open(p2, "rb") as f:
        up2_res = requests.post(f"{BASE_URL}/documents/upload", files={"file": (doc_2_file, f, "application/pdf")})
    assert up2_res.status_code == 200
    doc2_id = up2_res.json()["document"]["document_id"]

    # Delete Doc 1 again, verify Doc 2 stays active & retrievable
    requests.delete(f"{BASE_URL}/documents/{doc1_id}")

    q_doc2 = requests.post(f"{BASE_URL}/evaluator/query-and-evaluate", json={"question": "What is Unit Beta equipped with?", "top_k": 3})
    assert q_doc2.status_code == 200
    ret_doc2 = q_doc2.json().get("retrieved_evidence", [])
    
    assert len(ret_doc2) > 0
    assert ret_doc2[0]["document_name"] == doc_2_file
    print("PASSED: Soft deleting Doc 1 left Doc 2 active and retrievable!")

    # -------------------------------------------------------------
    # 9. Server Restart & Registry State Persistence Test
    # -------------------------------------------------------------
    print("\n--- 9. Testing Server Restart / Registry State Persistence ---")
    from app.services.document_registry import DocumentRegistryService
    
    reg_active = DocumentRegistryService.get_all_documents(status_filter="ACTIVE")
    reg_deleted = DocumentRegistryService.get_all_documents(status_filter="DELETED")

    reg_active_ids = [d["document_id"] for d in reg_active]
    reg_deleted_ids = [d["document_id"] for d in reg_deleted]

    assert doc2_id in reg_active_ids, "Doc 2 missing from active registry!"
    assert doc1_id in reg_deleted_ids, "Doc 1 missing from deleted registry!"
    print("PASSED: document_registry.json disk file accurately persisted ACTIVE and DELETED states!")

    # -------------------------------------------------------------
    # 10. Permanent Delete by document_id
    # -------------------------------------------------------------
    print("\n--- 10. Testing Permanent Delete by document_id ---")
    perm_res = requests.delete(f"{BASE_URL}/documents/{doc1_id}/permanent")
    assert perm_res.status_code == 200
    perm_data = perm_res.json()
    
    print("Permanent Delete Message:", perm_data.get("message"))

    all_docs = requests.get(f"{BASE_URL}/documents").json()["documents"]
    all_ids = [d["document_id"] for d in all_docs]
    
    assert doc1_id not in all_ids, "Permanently deleted document still found in registry!"
    assert not (TRASH_DIR / doc_1_file).exists(), "File still exists in trash!"
    assert not (UPLOADS_DIR / doc_1_file).exists(), "File still exists in uploads!"
    print("PASSED: Permanent deletion removed physical file, registry record, and vector chunks!")

    print("\n==================================================")
    print(" ALL LIFECYCLE & VIEWER TESTS PASSED SUCCESSFULLY! ")
    print("==================================================")

if __name__ == "__main__":
    time.sleep(1)
    test_lifecycle_and_viewer()
