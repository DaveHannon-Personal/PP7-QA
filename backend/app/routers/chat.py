"""
Chat router — streaming AI chat powered by Ollama.

The AI assistant has context about PP7 rules and can parse user intent
to produce structured rule definitions.

GET  /api/chat/history  — returns empty (session-only; no persistence in Phase 1)
POST /api/chat          — streaming chat completion (SSE)
POST /api/chat/parse-rule — non-streaming: extract rule JSON from conversation
"""
import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.audit import ChatRequest, ChatMessage
from app.services.ollama_client import chat, list_models

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("")
async def chat_endpoint(body: ChatRequest, db: Session = Depends(get_db)):
    """
    Streaming chat endpoint.
    Returns Server-Sent Events (SSE) — each event is a text/delta chunk.
    """
    messages = [m.model_dump() for m in body.messages]

    async def event_stream():
        try:
            gen = await chat(db, messages, stream=True)
            async for chunk in gen:
                # SSE format: "data: <content>\n\n"
                yield f"data: {json.dumps({'content': chunk})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/parse-rule")
async def parse_rule_endpoint(body: ChatRequest, db: Session = Depends(get_db)):
    """
    Non-streaming endpoint that asks the AI to produce a structured rule definition.
    Returns the full response; the frontend extracts the JSON block.
    """
    messages = [m.model_dump() for m in body.messages]
    # Append instruction to ensure structured output
    messages.append({
        "role": "user",
        "content": (
            "Based on our conversation, produce ONLY the JSON rule block "
            "in the format I described. No extra text."
        ),
    })
    response = await chat(db, messages, stream=False)
    content = response["choices"][0]["message"]["content"]
    return {"content": content}


@router.get("/models")
async def get_models(db: Session = Depends(get_db)):
    """List available Ollama models."""
    try:
        models = await list_models(db)
        return {"models": models}
    except Exception as exc:
        return {"models": [], "error": str(exc)}
