from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.documents import router as documents_router
from app.api.rag import router as rag_router
from app.api.quality import router as quality_router
from app.api.evaluator_api import router as evaluator_router
from app.api.nova_api import router as nova_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="RAGX Backend API — Data Quality & Answer Reliability Evaluation Engine",
    version="3.1.0"
)

# Enable CORS for local Vite React development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(documents_router, prefix=settings.API_PREFIX)
app.include_router(rag_router, prefix=settings.API_PREFIX)
app.include_router(quality_router, prefix=settings.API_PREFIX)
app.include_router(evaluator_router, prefix=settings.API_PREFIX)
app.include_router(nova_router, prefix=settings.API_PREFIX)






@app.get("/")
async def root():
    return {
        "status": "online",
        "app": "RAGX Backend Engine",
        "phase": "Phase 1 — Basic RAG Pipeline",
        "docs_url": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
