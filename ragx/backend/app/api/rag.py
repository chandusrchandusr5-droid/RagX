from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.rag_engine import rag_engine

router = APIRouter(prefix="/rag", tags=["RAG Pipeline"])

class QueryRequest(BaseModel):
    question: str
    top_k: int = 3

@router.post("/query")
async def query_rag_pipeline(request: QueryRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        result = rag_engine.query(question=request.question, top_k=request.top_k)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG query execution failed: {str(e)}")
