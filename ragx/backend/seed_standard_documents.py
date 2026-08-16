"""
RAGX Standard Baseline Document Seed Utility
Populates the standard attendance policy knowledge base documents:
- Attendance_Policy.pdf
- Attendance_Rules_v2.pdf
- Attendance_Policy_Copy.pdf

Uses the exact test fixture text and standard ingestion pipeline:
DocumentParser -> RAGEngine vector indexing -> DocumentRegistryService persistence.
"""
import pymupdf as fitz
from pathlib import Path
import hashlib
from app.core.config import settings
from app.services.document_parser import DocumentParser
from app.services.document_registry import DocumentRegistryService
from app.services.rag_engine import rag_engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ragx.seed_documents")

ATTENDANCE_POLICY_TEXTS = [
    "COLLEGE OF ENGINEERING & TECHNOLOGY\nACADEMIC POLICY MANUAL — SECTION 4: ATTENDANCE RULES\n1. GENERAL ATTENDANCE REQUIREMENT:\nAll undergraduate and postgraduate students enrolled in degree programs must maintain a minimum attendance of 75% in every course module during a semester.",
    "COLLEGE OF ENGINEERING & TECHNOLOGY\nACADEMIC POLICY MANUAL — SECTION 5: GRADING RULES\nGrade O: 90% and above."
]

ATTENDANCE_RULES_V2_TEXTS = [
    "COLLEGE OF ENGINEERING & TECHNOLOGY\nREVISED ACADEMIC REGULATION 2026\nSECTION 4: ATTENDANCE MANDATE\nAll enrolled undergraduate students must maintain a minimum attendance of 80% in every course module."
]

def create_pdf_bytes(pages_text: list[str]) -> bytes:
    doc = fitz.open()
    for text in pages_text:
        page = doc.new_page()
        if text:
            page.insert_textbox(fitz.Rect(50, 50, 550, 750), text, fontsize=10)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes

def seed_document(filename: str, pages_text: list[str]) -> dict:
    upload_path = settings.UPLOAD_DIR / filename
    pdf_bytes = create_pdf_bytes(pages_text)

    # 1. Write file to uploads directory
    with open(upload_path, "wb") as f:
        f.write(pdf_bytes)

    file_size_str = f"{len(pdf_bytes) / 1024:.2f} KB"
    file_hash = hashlib.md5(pdf_bytes).hexdigest()

    # 2. Parse text & pages
    parsed = DocumentParser.parse_document(upload_path)
    
    # 3. Register document in document_registry.json
    doc_record = DocumentRegistryService.register_document(
        document_name=filename,
        active_path=upload_path,
        total_pages=parsed["total_pages"],
        total_chunks=0,
        file_size_str=file_size_str,
        file_hash=file_hash
    )
    doc_id = doc_record["document_id"]

    # 4. Index chunks into ChromaDB
    chunks_count = rag_engine.index_document_chunks(
        file_name=filename,
        pages=parsed["pages"],
        document_id=doc_id
    )

    # 5. Update chunk count in registry
    updated_doc = DocumentRegistryService.update_document_chunks(doc_id, chunks_count)
    logger.info(f"Seeded document '{filename}' (ID: {doc_id}) -> {chunks_count} vector chunks indexed.")
    return updated_doc or doc_record

def seed_standard_baseline():
    print("==================================================")
    print(" SEEDING RAGX STANDARD ATTENDANCE BASELINE        ")
    print("==================================================")

    # 1. Seed Attendance_Policy.pdf
    d1 = seed_document("Attendance_Policy.pdf", ATTENDANCE_POLICY_TEXTS)
    print(f"1. Seeding 'Attendance_Policy.pdf' -> ID: {d1['document_id']}, Status: {d1['status']}, Chunks: {d1['total_chunks']}")

    # 2. Seed Attendance_Rules_v2.pdf
    d2 = seed_document("Attendance_Rules_v2.pdf", ATTENDANCE_RULES_V2_TEXTS)
    print(f"2. Seeding 'Attendance_Rules_v2.pdf' -> ID: {d2['document_id']}, Status: {d2['status']}, Chunks: {d2['total_chunks']}")

    # 3. Seed Attendance_Policy_Copy.pdf
    d3 = seed_document("Attendance_Policy_Copy.pdf", ATTENDANCE_POLICY_TEXTS)
    print(f"3. Seeding 'Attendance_Policy_Copy.pdf' -> ID: {d3['document_id']}, Status: {d3['status']}, Chunks: {d3['total_chunks']}")

    print("\n==================================================")
    print(" STANDARD BASELINE DOCUMENTS SEEDED SUCCESSFULLY! ")
    print("==================================================")

if __name__ == "__main__":
    seed_standard_baseline()
