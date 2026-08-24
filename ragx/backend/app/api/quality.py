from fastapi import APIRouter, HTTPException, Depends, Query
from app.services.data_quality import DataQualityService
from app.core.dependencies import get_optional_user

router = APIRouter(prefix="/quality", tags=["Data Quality"])

@router.get("/audit")
async def get_data_quality_audit(
    document_id: str | None = Query(None, description="Optional document ID or filename to audit individually"),
    current_user: dict | None = Depends(get_optional_user)
):
    owner_id = current_user["id"] if current_user else "legacy_dev_owner"
    try:
        service = DataQualityService()
        report = service.audit_knowledge_base(owner_id=owner_id, document_id=document_id)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Data Quality Audit failed: {str(e)}")
