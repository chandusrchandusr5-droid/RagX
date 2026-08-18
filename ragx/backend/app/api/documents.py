from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends
from fastapi.responses import FileResponse
from pathlib import Path
import shutil
import os
import hashlib
import uuid
import logging
from datetime import datetime
from app.core.config import settings
from app.core.vector_db import vector_db
from app.services.document_parser import DocumentParser
from app.services.rag_engine import rag_engine
from app.services.document_registry import DocumentRegistryService

from app.core.dependencies import get_optional_user
from app.services.auth_service import AuthService

logger = logging.getLogger("ragx.documents_api")

router = APIRouter(prefix="/documents", tags=["Documents"])

def calculate_file_hash(file_path: Path) -> str:
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

@router.post("/upload")
async def upload_document(file: UploadFile = File(...), current_user: dict | None = Depends(get_optional_user)):
    filename = file.filename
    ext = Path(filename).suffix.lower()

    if ext not in [".pdf", ".txt", ".md"]:
        raise HTTPException(status_code=400, detail=f"Unsupported file format '{ext}'. Only PDF, TXT, and MD files are supported.")

    owner_id = current_user["id"] if current_user else "legacy_dev_owner"

    # Save to upload dir
    save_path = settings.UPLOAD_DIR / filename
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size_bytes = save_path.stat().st_size
    file_size_kb = round(file_size_bytes / 1024, 2)
    file_hash = calculate_file_hash(save_path)

    try:
        owner_id = current_user["id"] if current_user else "default_workspace"

        # Check existing registry record to preserve document_id on re-upload
        existing_doc = DocumentRegistryService.get_document_by_name(filename, status_filter=None, owner_id=owner_id)
        doc_id = existing_doc.get("document_id") if existing_doc else f"doc_{uuid.uuid4().hex[:12]}"
        
        # Parse document
        parsed_doc = DocumentParser.parse_document(save_path)

        # Purge any existing vector chunks for this document_id prior to indexing
        vector_db.delete_document_chunks_by_id(doc_id, owner_id=owner_id)

        # Index chunks in ChromaDB tagged with document_id and owner_id
        num_chunks = rag_engine.index_document_chunks(
            file_name=filename,
            pages=parsed_doc["pages"],
            document_id=doc_id,
            owner_id=owner_id
        )

        # Register document state in a single clean write
        registered = DocumentRegistryService.register_document(
            document_name=filename,
            active_path=save_path,
            total_pages=parsed_doc["total_pages"],
            total_chunks=num_chunks,
            file_size_str=f"{file_size_kb} KB",
            file_hash=file_hash,
            owner_id=owner_id
        )

        if current_user:
            AuthService.log_activity(current_user["id"], current_user["full_name"], current_user["email"], "PDF Uploaded", f"Uploaded document '{filename}'.")

        return {
            "message": "Document uploaded and indexed successfully",
            "document": registered
        }

    except Exception as e:
        logger.error(f"Error processing document upload '{filename}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")


@router.get("")
async def list_documents(status: str = Query(None, description="Filter documents by status: ACTIVE or DELETED"), current_user: dict | None = Depends(get_optional_user)):
    owner_id = current_user["id"] if current_user else "legacy_dev_owner"
    documents = DocumentRegistryService.get_all_documents(status_filter=status, owner_id=owner_id)
    return {
        "total_documents": len(documents),
        "documents": documents
    }


@router.get("/{document_id}/view")
async def view_document(document_id: str, current_user: dict | None = Depends(get_optional_user)):
    """
    Secure inline PDF / Document Viewer endpoint.
    Serves active or trash files using document_id.
    Guarantees strict path traversal protection.
    """
    owner_id = current_user["id"] if (current_user and current_user.get("role") != "ADMIN") else None
    doc = DocumentRegistryService.get_document_by_id(document_id, owner_id=owner_id)
    if not doc:
        # Fallback search by filename if legacy call
        doc = DocumentRegistryService.get_document_by_name(document_id, status_filter=None, owner_id=owner_id)

    if not doc:
        raise HTTPException(status_code=404, detail=f"Document with ID '{document_id}' not found in registry.")

    # Determine file path based on status
    target_path = Path(doc["active_path"]) if doc["status"] == "ACTIVE" else Path(doc["trash_path"])

    if not target_path.exists():
        # Fallback check upload & trash dirs
        target_path = settings.UPLOAD_DIR / doc["document_name"]
        if not target_path.exists():
            target_path = settings.TRASH_DIR / doc["document_name"]

    if not target_path.exists():
        raise HTTPException(status_code=404, detail=f"Physical file for document '{doc['document_name']}' not found on server.")

    # Path traversal security verification
    resolved = target_path.resolve()
    allowed_dirs = [settings.UPLOAD_DIR.resolve(), settings.TRASH_DIR.resolve()]
    if not any(allowed in resolved.parents or allowed == resolved.parent for allowed in allowed_dirs):
        raise HTTPException(status_code=403, detail="Forbidden: Path traversal or unauthorized directory access.")

    ext = target_path.suffix.lower()
    media_type = "application/pdf" if ext == ".pdf" else "text/plain"

    return FileResponse(
        path=str(resolved),
        media_type=media_type,
        headers={
            "Content-Disposition": f"inline; filename=\"{doc['document_name']}\"",
            "Cache-Control": "no-cache"
        }
    )


@router.delete("/{document_id}")
async def soft_delete_document(document_id: str, current_user: dict | None = Depends(get_optional_user)):
    """
    Soft-deletes a document (ACTIVE -> DELETED).
    Moves file to TRASH_DIR and purges ChromaDB vector chunks by document_id.
    """
    owner_id = current_user["id"] if current_user else "legacy_dev_owner"
    doc = DocumentRegistryService.get_document_by_id(document_id, owner_id=owner_id)
    if not doc:
        doc = DocumentRegistryService.get_document_by_name(document_id, status_filter="ACTIVE", owner_id=owner_id)

    if not doc:
        raise HTTPException(status_code=404, detail=f"Active document with ID '{document_id}' not found.")

    doc_id = doc["document_id"]
    filename = doc["document_name"]

    # 1. Move file to trash directory
    active_path = Path(doc["active_path"])
    trash_path = Path(doc["trash_path"])

    if active_path.exists():
        try:
            shutil.move(str(active_path), str(trash_path))
            logger.info(f"Moved file '{filename}' to trash '{trash_path}'.")
        except Exception as e:
            logger.warning(f"Error moving file to trash: {e}")

    # 2. Purge ChromaDB vector chunks by document_id
    deleted_chunks = vector_db.delete_document_chunks_by_id(doc_id, owner_id=owner_id)

    # 3. Update registry state
    updated = DocumentRegistryService.soft_delete_document(doc_id, owner_id=owner_id)

    if current_user:
        AuthService.log_activity(current_user["id"], current_user["full_name"], current_user["email"], "PDF Deleted", f"Soft deleted document '{filename}'.")

    return {
        "message": f"Document '{filename}' moved to Deleted Documents (Trash).",
        "document_id": doc_id,
        "deleted_chunks": deleted_chunks,
        "document": updated
    }


@router.post("/{document_id}/restore")
async def restore_document(document_id: str, current_user: dict | None = Depends(get_optional_user)):
    """
    Restores a soft-deleted document (DELETED -> ACTIVE).
    Moves file back to UPLOAD_DIR and re-indexes ChromaDB vector chunks.
    """
    owner_id = current_user["id"] if current_user else "legacy_dev_owner"
    doc = DocumentRegistryService.get_document_by_id(document_id, owner_id=owner_id)
    if not doc:
        doc = DocumentRegistryService.get_document_by_name(document_id, status_filter="DELETED", owner_id=owner_id)

    if not doc:
        raise HTTPException(status_code=404, detail=f"Deleted document with ID '{document_id}' not found in trash.")

    doc_id = doc["document_id"]
    filename = doc["document_name"]

    trash_path = Path(doc["trash_path"])
    active_path = Path(doc["active_path"])

    # 1. Move file back to active upload directory
    if trash_path.exists():
        try:
            shutil.move(str(trash_path), str(active_path))
            logger.info(f"Restored file '{filename}' back to upload dir '{active_path}'.")
        except Exception as e:
            logger.error(f"Failed to restore file from trash: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to restore physical file from trash: {e}")
    elif not active_path.exists():
        raise HTTPException(status_code=404, detail=f"Physical file for '{filename}' not found in trash.")

    # 2. Re-parse and re-index vector chunks in ChromaDB
    parsed_doc = DocumentParser.parse_document(active_path)
    vector_db.delete_document_chunks_by_id(doc_id, owner_id=owner_id)
    num_chunks = rag_engine.index_document_chunks(
        file_name=filename,
        pages=parsed_doc["pages"],
        document_id=doc_id,
        owner_id=owner_id
    )

    # 3. Update registry status
    DocumentRegistryService.restore_document(doc_id, owner_id=owner_id)
    updated = DocumentRegistryService.update_document_chunks(doc_id, num_chunks)

    if current_user:
        AuthService.log_activity(current_user["id"], current_user["full_name"], current_user["email"], "PDF Restored", f"Restored document '{filename}'.")

    return {
        "message": f"Document '{filename}' restored to Active Knowledge Base.",
        "document_id": doc_id,
        "reindexed_chunks": num_chunks,
        "document": updated
    }


@router.delete("/{document_id}/permanent")
async def permanently_delete_document(document_id: str, current_user: dict | None = Depends(get_optional_user)):
    """
    Permanently deletes a document from disk, purges metadata, and removes all ChromaDB vector chunks.
    """
    owner_id = current_user["id"] if current_user else "legacy_dev_owner"
    doc = DocumentRegistryService.get_document_by_id(document_id, owner_id=owner_id)
    if not doc:
        doc = DocumentRegistryService.get_document_by_name(document_id, status_filter=None, owner_id=owner_id)

    if not doc:
        raise HTTPException(status_code=404, detail=f"Document with ID '{document_id}' not found.")

    doc_id = doc["document_id"]
    filename = doc["document_name"]

    # 1. Remove physical file from disk (check active and trash paths)
    for path_str in [doc.get("active_path"), doc.get("trash_path")]:
        if path_str:
            p = Path(path_str)
            if p.exists():
                try:
                    p.unlink()
                    logger.info(f"Permanently unlinked physical file '{p}'.")
                except Exception as e:
                    logger.warning(f"Error unlinking file '{p}': {e}")

    # Fallback check file names in upload/trash dirs
    for folder in [settings.UPLOAD_DIR, settings.TRASH_DIR]:
        fallback_file = folder / filename
        if fallback_file.exists():
            try:
                fallback_file.unlink()
            except Exception:
                pass

    # 2. Purge ChromaDB vector chunks
    deleted_chunks = vector_db.delete_document_chunks_by_id(doc_id, owner_id=owner_id)

    # 3. Permanently remove from registry JSON
    removed_record = DocumentRegistryService.permanently_delete_document(doc_id, owner_id=owner_id)

    if current_user:
        AuthService.log_activity(current_user["id"], current_user["full_name"], current_user["email"], "PDF Permanently Deleted", f"Permanently deleted document '{filename}'.")

    return {
        "message": f"Document '{filename}' permanently deleted.",
        "document_id": doc_id,
        "deleted_chunks": deleted_chunks,
        "removed_record": removed_record
    }
