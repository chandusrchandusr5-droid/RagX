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
    def get_all_documents(cls, status_filter: str = None, owner_id: str = None) -> list[dict]:
        records = cls._load_registry()
        filtered = []
        for r in records:
            r_owner = r.get("owner_id", "legacy_dev_owner")
            if owner_id is not None and r_owner != owner_id:
                continue
            if status_filter and r.get("status") != status_filter:
                continue
            filtered.append(r)
        return filtered

    @classmethod
    def get_document_by_id(cls, document_id: str, owner_id: str = None) -> dict | None:
        records = cls._load_registry()
        for r in records:
            if r.get("document_id") == document_id:
                r_owner = r.get("owner_id", "legacy_dev_owner")
                if owner_id is None or r_owner == owner_id:
                    return r
        return None

    @classmethod
    def get_document_by_name(cls, document_name: str, status_filter: str = "ACTIVE", owner_id: str = None) -> dict | None:
        records = cls._load_registry()
        for r in records:
            if r.get("document_name") == document_name:
                r_owner = r.get("owner_id", "legacy_dev_owner")
                if owner_id is None or r_owner == owner_id:
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
        owner_id: str = "legacy_dev_owner",
        registry_file_path: Path = None,
        uploads_dir_path: Path = None,
        trash_dir_path: Path = None
    ) -> dict:
        records = cls._load_registry(registry_file_path=registry_file_path)
        trash_dir = trash_dir_path or settings.TRASH_DIR
        
        # Check if an existing document record with same filename and owner exists
        existing = next((r for r in records if r.get("document_name") == document_name and r.get("owner_id", "legacy_dev_owner") == owner_id), None)

        doc_id = existing.get("document_id") if existing else f"doc_{uuid.uuid4().hex[:12]}"
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        doc_record = {
            "document_id": doc_id,
            "document_name": document_name,
            "original_filename": document_name,
            "owner_id": owner_id,
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
    def soft_delete_document(cls, document_id: str, owner_id: str = None) -> dict | None:
        records = cls._load_registry()
        for r in records:
            if r.get("document_id") == document_id:
                r_owner = r.get("owner_id", "legacy_dev_owner")
                if owner_id is None or r_owner == owner_id:
                    r["status"] = "DELETED"
                    r["deletion_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cls._save_registry(records)
                    return r
        return None

    @classmethod
    def restore_document(cls, document_id: str, owner_id: str = None) -> dict | None:
        records = cls._load_registry()
        for r in records:
            if r.get("document_id") == document_id:
                r_owner = r.get("owner_id", "legacy_dev_owner")
                if owner_id is None or r_owner == owner_id:
                    r["status"] = "ACTIVE"
                    r["deletion_date"] = None
                    cls._save_registry(records)
                    return r
        return None

    @classmethod
    def permanently_delete_document(cls, document_id: str, owner_id: str = None) -> dict | None:
        records = cls._load_registry()
        target = None
        for r in records:
            if r.get("document_id") == document_id:
                r_owner = r.get("owner_id", "legacy_dev_owner")
                if owner_id is None or r_owner == owner_id:
                    target = r
                    break
        if target:
            records = [r for r in records if r.get("document_id") != document_id]
            cls._save_registry(records)
            return target
        return None
