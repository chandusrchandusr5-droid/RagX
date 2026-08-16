"""
RAGX Actual Process Restart Test Helper
Step 1: Uploads Doc_Keep_Active.pdf and Doc_Keep_Deleted.pdf. Soft deletes Doc_Keep_Deleted.pdf.
Step 2: Can be invoked post-restart to assert API state persistence.
"""
import requests
import pymupdf as fitz
from pathlib import Path
import shutil
import sys

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

def setup_phase():
    print("--- SETUP PHASE: Uploading documents & soft-deleting ---")
    p1 = create_pdf("Doc_Keep_Active.pdf", "ACTIVE SERVER DOCUMENT CONTENT 2026\nThis document must stay ACTIVE across server restart.")
    with open(p1, "rb") as f:
        r1 = requests.post(f"{BASE_URL}/documents/upload", files={"file": ("Doc_Keep_Active.pdf", f, "application/pdf")})
    assert r1.status_code == 200
    id1 = r1.json()["document"]["document_id"]

    p2 = create_pdf("Doc_Keep_Deleted.pdf", "DELETED SERVER DOCUMENT CONTENT 2026\nThis document must stay DELETED in trash across server restart.")
    with open(p2, "rb") as f:
        r2 = requests.post(f"{BASE_URL}/documents/upload", files={"file": ("Doc_Keep_Deleted.pdf", f, "application/pdf")})
    assert r2.status_code == 200
    id2 = r2.json()["document"]["document_id"]

    del_res = requests.delete(f"{BASE_URL}/documents/{id2}")
    assert del_res.status_code == 200

    print("Setup completed. Doc_Keep_Active ID:", id1, "ACTIVE")
    print("Setup completed. Doc_Keep_Deleted ID:", id2, "DELETED")

def verify_phase():
    print("--- VERIFY PHASE: Checking state persistence post-restart ---")
    act_res = requests.get(f"{BASE_URL}/documents?status=ACTIVE").json()
    del_res = requests.get(f"{BASE_URL}/documents?status=DELETED").json()

    act_names = [d.get("document_name") or d.get("file_name") for d in act_res.get("documents", [])]
    del_names = [d.get("document_name") or d.get("file_name") for d in del_res.get("documents", [])]

    print("Active documents in API post-restart:", act_names)
    print("Deleted documents in API post-restart:", del_names)


    assert "Doc_Keep_Active.pdf" in act_names, "Doc_Keep_Active.pdf missing from ACTIVE list post-restart!"
    assert "Doc_Keep_Deleted.pdf" in del_names, "Doc_Keep_Deleted.pdf missing from DELETED list post-restart!"
    assert "Doc_Keep_Active.pdf" not in del_names
    assert "Doc_Keep_Deleted.pdf" not in act_names

    # Verify RAG retrieval
    q_act = requests.post(f"{BASE_URL}/evaluator/query-and-evaluate", json={"question": "What is in the active server document?", "top_k": 3}).json()
    ret_act = q_act.get("retrieved_evidence", [])
    assert len(ret_act) > 0
    assert ret_act[0]["document_name"] == "Doc_Keep_Active.pdf"

    q_del = requests.post(f"{BASE_URL}/evaluator/query-and-evaluate", json={"question": "What is in the deleted server document?", "top_k": 3}).json()
    ret_del = q_del.get("retrieved_evidence", [])
    assert len([c for c in ret_del if c.get("document_name") == "Doc_Keep_Deleted.pdf"]) == 0

    print("==================================================")
    print(" ACTUAL SERVER RESTART PERSISTENCE VERIFIED 100%! ")
    print("==================================================")

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "setup"
    if mode == "setup":
        setup_phase()
    elif mode == "verify":
        verify_phase()
