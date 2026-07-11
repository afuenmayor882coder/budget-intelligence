"""AI Financial Chat API routes — Phase 5."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.database import db_context
from services.chat_service import chat, get_suggested_questions

router = APIRouter(prefix="/chat", tags=["chat"])

# In-memory conversation store keyed by conversation_id.
# For a production system this would persist to the DB.
_conversations: dict[str, list[dict[str, str]]] = {}


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = "default"
    anthropic_api_key: Optional[str] = ""
    openai_api_key: Optional[str] = ""


class ChatResponse(BaseModel):
    reply: str
    category: str
    mode: str
    source: str
    timestamp: str
    conversation_id: str


@router.post("/message", response_model=ChatResponse)
def send_message(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    conv_id = req.conversation_id or "default"
    history = _conversations.setdefault(conv_id, [])

    with db_context() as conn:
        result = chat(
            user_message=req.message,
            conversation_history=history,
            conn=conn,
            anthropic_key=req.anthropic_api_key or "",
            openai_key=req.openai_api_key or "",
        )

    # Append to history
    history.append({"role": "user", "content": req.message})
    history.append({"role": "assistant", "content": result["reply"]})
    # Keep last 40 messages
    _conversations[conv_id] = history[-40:]

    return ChatResponse(
        reply=result["reply"],
        category=result["category"],
        mode=result["mode"],
        source=result["source"],
        timestamp=result["timestamp"],
        conversation_id=conv_id,
    )


@router.get("/history/{conversation_id}")
def get_history(conversation_id: str = "default"):
    return {"conversation_id": conversation_id, "messages": _conversations.get(conversation_id, [])}


@router.delete("/history/{conversation_id}")
def clear_history(conversation_id: str = "default"):
    _conversations.pop(conversation_id, None)
    return {"status": "cleared", "conversation_id": conversation_id}


@router.get("/suggestions")
def get_suggestions():
    with db_context() as conn:
        questions = get_suggested_questions(conn)
    return {"suggestions": questions}


@router.get("/status")
def chat_status():
    from core.config import settings
    return {
        "rule_based": True,
        "llm_enabled": settings.llm_enabled,
        "anthropic_configured": bool(settings.anthropic_api_key),
        "openai_configured": bool(settings.openai_api_key),
    }
