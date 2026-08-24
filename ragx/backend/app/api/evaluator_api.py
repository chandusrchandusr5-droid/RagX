from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from app.services.evaluator import AnswerEvaluator
from app.services.rag_engine import rag_engine
from app.services.evaluation_history import EvaluationHistoryService

from app.core.dependencies import get_optional_user

router = APIRouter(prefix="/evaluator", tags=["RAG Answer Reliability Evaluator"])


class EvaluationRequest(BaseModel):
    query: str
    answer: str
    retrieved_evidence: Optional[List[Dict[str, Any]]] = []

class QueryAndEvaluateRequest(BaseModel):
    question: str
    top_k: int = 3

@router.post("/evaluate")
async def evaluate_rag_answer(request: EvaluationRequest, current_user: dict | None = Depends(get_optional_user)):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    owner_id = current_user["id"] if current_user else "legacy_dev_owner"

    try:
        evidence = request.retrieved_evidence
        if not evidence and request.query.strip():
            # Fallback: Retrieve Top-K evidence from ChromaDB knowledge base if omitted in custom evaluation
            rag_result = rag_engine.query(question=request.query, owner_id=owner_id, top_k=3)
            evidence = rag_result.get("retrieved_evidence", [])

        service = AnswerEvaluator()
        report = service.evaluate(
            query=request.query,
            answer=request.answer,
            retrieved_evidence=evidence or [],
            owner_id=owner_id
        )
        EvaluationHistoryService.log_evaluation_run(report, owner_id=owner_id)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Answer evaluation failed: {str(e)}")

@router.post("/query-and-evaluate")
async def query_and_evaluate_rag(request: QueryAndEvaluateRequest, current_user: dict | None = Depends(get_optional_user)):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    owner_id = current_user["id"] if current_user else "legacy_dev_owner"

    try:
        # Step 1: Execute RAG Pipeline Query
        rag_result = rag_engine.query(question=request.question, owner_id=owner_id, top_k=request.top_k)
        
        # Step 2: Execute Answer Reliability Evaluation
        service = AnswerEvaluator()
        eval_report = service.evaluate(
            query=request.question,
            answer=rag_result.get("answer", ""),
            retrieved_evidence=rag_result.get("retrieved_evidence", []),
            owner_id=owner_id
        )

        # Save to history with owner_id
        EvaluationHistoryService.log_evaluation_run(eval_report, owner_id=owner_id)

        # Log Activity if user is logged in
        if current_user:
            from app.services.auth_service import AuthService
            AuthService.log_activity(
                current_user["id"], current_user["full_name"], current_user["email"],
                "Answer Evaluation", f"Evaluated query: '{request.question[:50]}...'"
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
async def get_evaluation_analytics(current_user: dict | None = Depends(get_optional_user)):
    """
    Returns aggregate evaluation analytics derived directly from persistent evaluation_history.json for the authenticated user.
    """
    owner_id = current_user["id"] if current_user else "legacy_dev_owner"
    try:
        return EvaluationHistoryService.get_analytics_summary(owner_id=owner_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compute evaluation analytics: {str(e)}")

@router.get("/history")
async def get_evaluation_history(limit: int = 50, current_user: dict | None = Depends(get_optional_user)):
    """
    Returns recent persisted evaluation runs for log inspection and audit traceability for the authenticated user.
    """
    owner_id = current_user["id"] if current_user else "legacy_dev_owner"
    try:
        records = EvaluationHistoryService.get_history(limit=limit, owner_id=owner_id)
        return {
            "total_records": len(records),
            "records": records
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch evaluation history: {str(e)}")

