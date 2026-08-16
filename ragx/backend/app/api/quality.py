from fastapi import APIRouter, HTTPException
from app.services.data_quality import DataQualityService

router = APIRouter(prefix="/quality", tags=["Data Quality"])

@router.get("/audit")
async def get_data_quality_audit():
    try:
        service = DataQualityService()
        report = service.audit_knowledge_base()
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Data Quality Audit failed: {str(e)}")

