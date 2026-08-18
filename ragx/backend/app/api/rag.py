from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.services.rag_engine import rag_engine
from app.core.dependencies import get_optional_user

router = APIRouter(prefix="/rag", tags=["RAG Pipeline"])

class QueryRequest(BaseModel):
    question: str
    top_k: int = 3

@router.post("/query")
async def query_rag_pipeline(request: QueryRequest, current_user: dict | None = Depends(get_optional_user)):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    owner_id = current_user["id"] if current_user else None

    try:
        result = rag_engine.query(question=request.question, owner_id=owner_id, top_k=request.top_k)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG query execution failed: {str(e)}")
