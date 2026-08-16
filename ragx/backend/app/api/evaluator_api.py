from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from app.services.evaluator import AnswerEvaluator
from app.services.rag_engine import rag_engine
from app.services.evaluation_history import EvaluationHistoryService

router = APIRouter(prefix="/evaluator", tags=["RAG Answer Reliability Evaluator"])


class EvaluationRequest(BaseModel):
    query: str
    answer: str
    retrieved_evidence: Optional[List[Dict[str, Any]]] = []

class QueryAndEvaluateRequest(BaseModel):
    question: str
    top_k: int = 3

@router.post("/evaluate")
async def evaluate_rag_answer(request: EvaluationRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    try:
        service = AnswerEvaluator()
        report = service.evaluate(
            query=request.query,
            answer=request.answer,
            retrieved_evidence=request.retrieved_evidence or []
        )
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Answer evaluation failed: {str(e)}")

@router.post("/query-and-evaluate")
async def query_and_evaluate_rag(request: QueryAndEvaluateRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        # Step 1: Execute RAG Pipeline Query
        rag_result = rag_engine.query(question=request.question, top_k=request.top_k)
        
        # Step 2: Execute Answer Reliability Evaluation
        service = AnswerEvaluator()
        eval_report = service.evaluate(
            query=request.question,
            answer=rag_result.get("answer", ""),
            retrieved_evidence=rag_result.get("retrieved_evidence", [])
        )

        return {
            "question": request.question,
            "answer": rag_result.get("answer"),
            "retrieved_evidence": rag_result.get("retrieved_evidence"),
            "total_evidence_chunks": len(rag_result.get("retrieved_evidence", [])),
            "evaluation_report": eval_report
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG query and evaluation failed: {str(e)}")

@router.get("/analytics")
async def get_evaluation_analytics():
    """
    Returns aggregate evaluation analytics derived directly from persistent evaluation_history.json.
    Includes total runs, average Answer Reliability Score, category breakdown, score distribution, and recent runs.
    """
    try:
        return EvaluationHistoryService.get_analytics_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compute evaluation analytics: {str(e)}")

@router.get("/history")
async def get_evaluation_history(limit: int = 50):
    """
    Returns recent persisted evaluation runs for log inspection and audit traceability.
    """
    try:
        records = EvaluationHistoryService.get_history(limit=limit)
        return {
            "total_records": len(records),
            "records": records
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch evaluation history: {str(e)}")

