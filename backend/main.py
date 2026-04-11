"""FastAPI backend for LLM Knesset."""

import os
import pathlib

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uuid
import json
import asyncio

from . import storage
from . import settings_store
from . import user_store
from . import auth
from .council import (
    run_full_council,
    generate_conversation_title,
    stage1_collect_responses,
    stage2_collect_rankings,
    stage3_synthesize_final,
    calculate_aggregate_rankings,
)

app = FastAPI(title="LLM Knesset API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Auth ──────────────────────────────────────────────────────────────────────

class FirebaseTokenRequest(BaseModel):
    id_token: str


@app.post("/auth/firebase")
async def firebase_login(request: Request, body: FirebaseTokenRequest):
    payload = await auth.verify_firebase_token(body.id_token)

    email = payload.get("email", "")
    name = payload.get("name", "")
    picture = payload.get("picture", "")
    sub = payload["sub"]

    admin_emails = settings_store.get_admin_emails()
    if not admin_emails:
        settings_store.add_admin_email(email)

    user = {"sub": sub, "email": email, "name": name, "picture": picture}
    token = auth.create_session_token(user)
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)

    response = JSONResponse({"success": True, "email": email, "name": name})
    response.set_cookie(
        auth.SESSION_COOKIE,
        token,
        max_age=auth.SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=(scheme == "https"),
    )
    return response


@app.post("/auth/logout")
async def logout():
    response = JSONResponse({"success": True})
    response.delete_cookie(auth.SESSION_COOKIE)
    return response


@app.get("/api/me")
async def get_me(user: dict = Depends(auth.require_user)):
    admin_emails = settings_store.get_admin_emails()
    return {
        "email": user["email"],
        "name": user["name"],
        "picture": user.get("picture", ""),
        "is_admin": user["email"] in admin_emails,
    }


# ── Conversations ──────────────────────────────────────────────────────────────

class CreateConversationRequest(BaseModel):
    pass


class SendMessageRequest(BaseModel):
    content: str


class ConversationMetadata(BaseModel):
    id: str
    created_at: str
    title: str
    message_count: int


class Conversation(BaseModel):
    id: str
    created_at: str
    title: str
    messages: List[Dict[str, Any]]



@app.get("/api/conversations", response_model=List[ConversationMetadata])
async def list_conversations(user: dict = Depends(auth.require_user)):
    return storage.list_conversations(user_id=user["sub"])


@app.post("/api/conversations", response_model=Conversation)
async def create_conversation(
    request: CreateConversationRequest,
    user: dict = Depends(auth.require_user),
):
    conversation_id = str(uuid.uuid4())
    return storage.create_conversation(conversation_id, user_id=user["sub"])


@app.get("/api/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(
    conversation_id: str,
    user: dict = Depends(auth.require_user),
):
    conversation = storage.get_conversation(conversation_id, user_id=user["sub"])
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.post("/api/conversations/{conversation_id}/message")
async def send_message(
    conversation_id: str,
    request: SendMessageRequest,
    user: dict = Depends(auth.require_user),
):
    conversation = storage.get_conversation(conversation_id, user_id=user["sub"])
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    is_first_message = len(conversation["messages"]) == 0
    storage.add_user_message(conversation_id, request.content)

    if is_first_message:
        title = await generate_conversation_title(request.content)
        storage.update_conversation_title(conversation_id, title)

    prefs = user_store.get_user_prefs(user["sub"])
    stage1_results, stage2_results, stage3_result, metadata = await run_full_council(
        request.content,
        council_models=prefs.get("council_models") or None,
        chairman_model=prefs.get("chairman_model") or None,
    )

    storage.add_assistant_message(conversation_id, stage1_results, stage2_results, stage3_result)
    return {"stage1": stage1_results, "stage2": stage2_results, "stage3": stage3_result, "metadata": metadata}


@app.post("/api/conversations/{conversation_id}/message/stream")
async def send_message_stream(
    conversation_id: str,
    request: SendMessageRequest,
    user: dict = Depends(auth.require_user),
):
    conversation = storage.get_conversation(conversation_id, user_id=user["sub"])
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    is_first_message = len(conversation["messages"]) == 0
    prefs = user_store.get_user_prefs(user["sub"])
    council_models = prefs.get("council_models") or None
    chairman_model = prefs.get("chairman_model") or None

    async def event_generator():
        try:
            storage.add_user_message(conversation_id, request.content)

            title_task = None
            if is_first_message:
                title_task = asyncio.create_task(generate_conversation_title(request.content))

            yield f"data: {json.dumps({'type': 'stage1_start'})}\n\n"
            stage1_results = await stage1_collect_responses(request.content, council_models=council_models)
            yield f"data: {json.dumps({'type': 'stage1_complete', 'data': stage1_results})}\n\n"

            yield f"data: {json.dumps({'type': 'stage2_start'})}\n\n"
            stage2_results, label_to_model = await stage2_collect_rankings(
                request.content, stage1_results, council_models=council_models
            )
            aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
            yield f"data: {json.dumps({'type': 'stage2_complete', 'data': stage2_results, 'metadata': {'label_to_model': label_to_model, 'aggregate_rankings': aggregate_rankings}})}\n\n"

            yield f"data: {json.dumps({'type': 'stage3_start'})}\n\n"
            stage3_result = await stage3_synthesize_final(
                request.content, stage1_results, stage2_results, chairman_model=chairman_model
            )
            yield f"data: {json.dumps({'type': 'stage3_complete', 'data': stage3_result})}\n\n"

            if title_task:
                title = await title_task
                storage.update_conversation_title(conversation_id, title)
                yield f"data: {json.dumps({'type': 'title_complete', 'data': {'title': title}})}\n\n"

            storage.add_assistant_message(conversation_id, stage1_results, stage2_results, stage3_result)
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


# ── User Preferences (all authenticated users) ────────────────────────────────

class UserPrefsRequest(BaseModel):
    council_models: Optional[List[str]] = None
    chairman_model: Optional[str] = None


@app.get("/api/prefs")
async def get_prefs(user: dict = Depends(auth.require_user)):
    prefs = user_store.get_user_prefs(user["sub"])
    return {
        "council_models": prefs.get("council_models") or settings_store.get_council_models(),
        "chairman_model": prefs.get("chairman_model") or settings_store.get_chairman_model(),
        "using_defaults": not prefs.get("council_models"),
    }


@app.put("/api/prefs")
async def update_prefs(request: UserPrefsRequest, user: dict = Depends(auth.require_user)):
    updates = {}
    if request.council_models is not None:
        updates["council_models"] = request.council_models
    if request.chairman_model is not None:
        updates["chairman_model"] = request.chairman_model
    user_store.update_user_prefs(user["sub"], updates)
    return {"success": True}


# ── Models (all authenticated users) ─────────────────────────────────────────

@app.get("/api/models")
async def list_openrouter_models(user: dict = Depends(auth.require_user)):
    import httpx
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get("https://openrouter.ai/api/v1/models", headers={"Accept": "application/json"})
            resp.raise_for_status()
            data = resp.json()
        models = []
        for m in data.get("data", []):
            arch = m.get("architecture", {})
            pricing = m.get("pricing", {})
            try:
                prompt_price = float(pricing.get("prompt", 0) or 0)
            except (ValueError, TypeError):
                prompt_price = 0.0
            models.append({
                "id": m["id"],
                "name": m.get("name", m["id"]),
                "context_length": m.get("context_length"),
                "modality": arch.get("modality", "text->text"),
                "price_per_million": round(prompt_price * 1_000_000, 4),
            })
        models = [m for m in models if not m["id"].startswith("openrouter/") and m["price_per_million"] >= 0]
        models.sort(key=lambda x: x["price_per_million"])
        return {"models": models}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch models: {e}")


# ── Admin Settings ────────────────────────────────────────────────────────────

class UpdateSettingsRequest(BaseModel):
    openrouter_api_key: Optional[str] = None
    council_models: Optional[List[str]] = None
    chairman_model: Optional[str] = None
    admin_emails: Optional[List[str]] = None


@app.get("/api/settings")
async def get_settings(user: dict = Depends(auth.require_admin)):
    s = settings_store.get_settings()
    key = s.get("openrouter_api_key", "")
    masked = ("•" * (len(key) - 4) + key[-4:]) if len(key) > 4 else ("•" * len(key))
    return {
        "openrouter_api_key_set": bool(key),
        "openrouter_api_key_preview": masked if key else "",
        "council_models": s.get("council_models", []),
        "chairman_model": s.get("chairman_model", ""),
        "admin_emails": s.get("admin_emails", []),
    }


@app.put("/api/settings")
async def update_settings(request: UpdateSettingsRequest, user: dict = Depends(auth.require_admin)):
    updates = {}
    if request.openrouter_api_key is not None:
        updates["openrouter_api_key"] = request.openrouter_api_key
    if request.council_models is not None:
        updates["council_models"] = request.council_models
    if request.chairman_model is not None:
        updates["chairman_model"] = request.chairman_model
    if request.admin_emails is not None:
        updates["admin_emails"] = request.admin_emails
    settings_store.update_settings(updates)
    return {"success": True}


@app.post("/api/settings/test")
async def test_connection(user: dict = Depends(auth.require_admin)):
    import httpx
    from .config import OPENROUTER_API_URL
    key = settings_store.get_api_key()
    if not key:
        return {"success": False, "error": "No API key configured"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                OPENROUTER_API_URL,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"model": "openai/gpt-4o-mini", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1},
            )
            if response.status_code == 200:
                return {"success": True}
            elif response.status_code == 401:
                return {"success": False, "error": "Invalid API key"}
            else:
                return {"success": False, "error": f"API returned status {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── Serve built frontend in production ────────────────────────────────────────

_DIST = pathlib.Path(__file__).parent.parent / "frontend" / "dist"

if _DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=str(_DIST / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        file = _DIST / full_path
        if file.is_file():
            return FileResponse(str(file))
        return FileResponse(str(_DIST / "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
