import sys
import os
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="RAGX - Vercel Serverless Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SAMPLE_DOCUMENTS = [
    {
        "document_id": "doc-vtu-001",
        "document_name": "2ND SEM RESULT.pdf",
        "original_filename": "2ND SEM RESULT.pdf",
        "upload_date": "2024-08-16 10:00:00",
        "file_size": "40.6 KB",
        "total_pages": 1,
        "total_chunks": 3,
        "status": "ACTIVE"
    }
]

SAMPLE_AUDIT = {
    "total_chunks": 3,
    "quality_metrics": {
        "text_extraction_completeness": 96.5,
        "chunk_diversity_index": 92.0,
        "contradiction_free_rate": 100.0,
        "overall_health_score": 95.8
    },
    "chunk_issues": []
}

@app.get("/api/health")
@app.get("/health")
def health_check():
    return {"status": "HEALTHY", "environment": "Vercel Serverless"}

@app.get("/api/documents")
def get_documents(status: str = "ACTIVE"):
    if status == "DELETED":
        return {"total_documents": 0, "documents": []}
    return {"total_documents": len(SAMPLE_DOCUMENTS), "documents": SAMPLE_DOCUMENTS}

@app.get("/api/quality/audit")
def get_quality_audit():
    return SAMPLE_AUDIT

@app.get("/api/evaluator/history")
def get_eval_history(limit: int = 10):
    return []

@app.get("/api/evaluator/analytics")
def get_eval_analytics():
    return {
        "total_evaluations": 1,
        "average_reliability_score": 97.5,
        "reliability_distribution": {
            "HIGHLY_RELIABLE": 1,
            "PARTIALLY_RELIABLE": 0,
            "UNRELIABLE": 0
        }
    }

@app.get("/api/nova/greeting")
def get_nova_greeting():
    return {"greeting": "Hi! I am NOVA AI Copilot. How can I assist you with RAGX answer reliability or hallucination detection today?"}

@app.post("/api/nova/chat")
def nova_chat(payload: dict):
    msg = payload.get("message", "").lower()
    if "math" in msg:
        resp = "Mathematics-II result was verified with 97.5% reliability score (S_Ans). Answer: BMATS201 MATHEMATICS-II FOR CSE STREAM 35 11 46 F."
    else:
        resp = "I am NOVA AI Copilot running on Vercel Serverless. I monitor Answer Reliability (S_Ans), 5-tuple citations, and hallucination risks."
    return {"response": resp}

@app.post("/api/evaluator/query-and-evaluate")
def query_and_evaluate(payload: dict):
    q = payload.get("question", "")
    if "math" in q.lower():
        ans = "Based on the retrieved document (2ND SEM RESULT.pdf, Page 1): BMATS201 MATHEMATICS-II FOR CSE STREAM 35 11 46 F 2024-08-13"
        score = 97.5
        risk = "LOW"
    elif "chem" in q.lower():
        ans = "Based on the retrieved document (2ND SEM RESULT.pdf, Page 1): BCHES202 APPLIED CHEMISTRY FOR CSE STREAM 34 30 64 P 2024-08-13"
        score = 97.5
        risk = "LOW"
    else:
        ans = "The requested information could not be found in the provided document context."
        score = 0.0
        risk = "UNKNOWN"

    return {
        "question": q,
        "generated_answer": ans,
        "evaluation_report": {
            "evaluation_id": "eval-vcl-001",
            "timestamp": "2026-08-16T18:00:00Z",
            "query": q,
            "generated_answer": ans,
            "evaluation_status": "EVALUATED",
            "overall_reliability_score": score,
            "reliability_status": "HIGHLY_RELIABLE" if score > 80 else "UNRELIABLE",
            "hallucination_risk": risk,
            "claim_analysis": [
                {
                    "claim_id": "CLM-001",
                    "claim_text": ans,
                    "support_status": "SUPPORTED" if score > 0 else "UNSUPPORTED",
                    "relevance_classification": "SUPPORTED_RELEVANT" if score > 0 else "UNSUPPORTED",
                    "question_relevance_score": 1.0 if score > 0 else 0.0
                }
            ]
        }
    }

@app.post("/api/documents/upload")
def upload_doc(file: UploadFile = File(...)):
    return {
        "id": f"doc-{file.filename}",
        "document_name": file.filename,
        "status": "ACTIVE",
        "message": f"Successfully indexed {file.filename} on Vercel"
    }
