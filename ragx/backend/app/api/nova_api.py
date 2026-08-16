from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.nova_service import nova_assistant

router = APIRouter(prefix="/nova", tags=["NOVA AI Copilot Assistant"])

class NovaChatRequest(BaseModel):
    message: str
    context_page: Optional[str] = "general"

@router.get("/greeting")
async def get_nova_greeting():
    """
    Returns initial NOVA greeting and suggested quick prompts upon application load.
    """
    try:
        return nova_assistant.get_welcome_greeting()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch NOVA greeting: {str(e)}")

@router.post("/chat")
async def chat_with_nova(request: NovaChatRequest):
    """
    Handles interactive user queries to NOVA AI Copilot.
    """
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    try:
        return nova_assistant.respond(
            message=request.message.strip(),
            context_page=request.context_page or "general"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"NOVA response failed: {str(e)}")
