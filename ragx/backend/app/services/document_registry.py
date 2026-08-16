import json
import uuid
import logging
from pathlib import Path
from datetime import datetime
from app.core.config import settings

logger = logging.getLogger("ragx.document_registry")

class DocumentRegistryService:
    @classmethod
    def _load_registry(cls, registry_file_path: Path = None) -> list[dict]:
        registry_file = registry_file_path or settings.REGISTRY_FILE
        if not registry_file.exists():
            return []
        try:
            with open(registry_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"Failed to read document registry file '{registry_file}': {e}")
            return []

    @classmethod
    def _save_registry(cls, records: list[dict], registry_file_path: Path = None):
        registry_file = registry_file_path or settings.REGISTRY_FILE
        try:
            with open(registry_file, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save document registry file '{registry_file}': {e}")

    @classmethod
    def get_all_documents(cls, status_filter: str = None) -> list[dict]:
        records = cls._load_registry()
        if status_filter:
            return [r for r in records if r.get("status") == status_filter]
        return records

    @classmethod
    def get_document_by_id(cls, document_id: str) -> dict | None:
        records = cls._load_registry()
        for r in records:
            if r.get("document_id") == document_id:
                return r
        return None

    @classmethod
    def get_document_by_name(cls, document_name: str, status_filter: str = "ACTIVE") -> dict | None:
        records = cls._load_registry()
        for r in records:
            if r.get("document_name") == document_name:
                if status_filter is None or r.get("status") == status_filter:
                    return r
        return None

    @classmethod
    def register_document(
        cls,
        document_name: str,
        active_path: Path,
        total_pages: int,
        total_chunks: int,
        file_size_str: str = "1.0 KB",
        file_hash: str = "dummy_hash",
        registry_file_path: Path = None,
        uploads_dir_path: Path = None,
        trash_dir_path: Path = None
    ) -> dict:
        records = cls._load_registry(registry_file_path=registry_file_path)
        trash_dir = trash_dir_path or settings.TRASH_DIR
        
        # Check if an existing document record with same filename exists
        existing = next((r for r in records if r.get("document_name") == document_name), None)

        
        doc_id = existing.get("document_id") if existing else f"doc_{uuid.uuid4().hex[:12]}"
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        doc_record = {
            "document_id": doc_id,
            "document_name": document_name,
            "original_filename": document_name,
            "status": "ACTIVE",
            "active_path": str(active_path),
            "trash_path": str(trash_dir / document_name),
            "upload_date": now_str,
            "deletion_date": None,
            "total_pages": total_pages,
            "total_chunks": total_chunks,
            "file_size": file_size_str,
            "file_hash": file_hash
        }

        if existing:
            existing.update(doc_record)
        else:
            records.append(doc_record)

        cls._save_registry(records, registry_file_path=registry_file_path)
        return doc_record

    @classmethod
    def update_document_chunks(cls, doc_id: str, chunks_count: int, registry_file_path: Path = None) -> dict | None:
        records = cls._load_registry(registry_file_path=registry_file_path)
        for r in records:
            if r.get("document_id") == doc_id:
                r["total_chunks"] = chunks_count
                cls._save_registry(records, registry_file_path=registry_file_path)
                return r

        return None

    @classmethod
    def soft_delete_document(cls, document_id: str) -> dict | None:
        records = cls._load_registry()
        for r in records:
            if r.get("document_id") == document_id:
                r["status"] = "DELETED"
                r["deletion_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cls._save_registry(records)
                return r
        return None

    @classmethod
    def restore_document(cls, document_id: str) -> dict | None:
        records = cls._load_registry()
        for r in records:
            if r.get("document_id") == document_id:
                r["status"] = "ACTIVE"
                r["deletion_date"] = None
                cls._save_registry(records)
                return r
        return None

    @classmethod
    def permanently_delete_document(cls, document_id: str) -> dict | None:
        records = cls._load_registry()
        target = next((r for r in records if r.get("document_id") == document_id), None)
        if target:
            records = [r for r in records if r.get("document_id") != document_id]
            cls._save_registry(records)
            return target
        return None
