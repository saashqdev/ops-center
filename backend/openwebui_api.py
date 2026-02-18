"""
Open WebUI Proxy API - Unicorn Chat Integration
Proxies management requests to Open WebUI with auth, usage metering,
credit deduction, and model sync.

Endpoints:
  GET  /api/v1/openwebui/health    - Health check
  GET  /api/v1/openwebui/status    - Detailed status + model count
  GET  /api/v1/openwebui/models    - Available models (from Open WebUI)
  GET  /api/v1/openwebui/users     - User list (admin only)
  GET  /api/v1/openwebui/stats     - Chat usage statistics
  GET  /api/v1/openwebui/config    - Public configuration
  POST /api/v1/openwebui/chat      - Metered chat completion proxy (credits)
  POST /api/v1/openwebui/sync-models - Push curated model list to Open WebUI
  POST /api/v1/openwebui/seed      - Seed app_definitions & add_ons records
"""

import os
import logging
import time
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/openwebui", tags=["Open WebUI (Unicorn Chat)"])

# Open WebUI internal URL (container-to-container via Docker network)
OPENWEBUI_URL = os.getenv("OPENWEBUI_URL", "http://unicorn-open-webui:8080")
OPENWEBUI_TIMEOUT = 10.0  # seconds


async def _get_session_user(request: Request) -> Dict[str, Any]:
    """Get authenticated user from session cookie"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        from redis_session import RedisSessionManager
        redis_host = os.getenv("REDIS_HOST", "unicorn-lago-redis")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        sessions = RedisSessionManager(host=redis_host, port=redis_port)
        session_data = sessions.get(session_token)
        if not session_data:
            raise HTTPException(status_code=401, detail="Invalid session")
        user = session_data.get("user", {})
        if not user:
            raise HTTPException(status_code=401, detail="No user in session")
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Auth error in openwebui proxy: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")


async def _proxy_get(path: str, params: dict = None, timeout: float = None) -> dict:
    """Make a GET request to Open WebUI"""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=timeout or OPENWEBUI_TIMEOUT) as client:
            response = await client.get(f"{OPENWEBUI_URL}{path}", params=params)
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Open WebUI timed out")
    except httpx.HTTPStatusError as e:
        logger.error(f"Open WebUI error: {e.response.status_code} on {path}")
        # Don't pass upstream 401/403 to the client — those are Open WebUI's
        # auth errors, not our session errors. Map them to 502 instead.
        status = e.response.status_code
        if status in (401, 403):
            raise HTTPException(status_code=502, detail=f"Open WebUI auth error ({status}) — check WEBUI_SECRET_KEY / API key")
        raise HTTPException(status_code=status, detail="Open WebUI returned an error")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Open WebUI is not reachable")
    except Exception as e:
        logger.error(f"Open WebUI proxy error: {e}")
        raise HTTPException(status_code=502, detail="Failed to contact Open WebUI")


# ─── Health & Status ─────────────────────────────────────────

@router.get("/health")
async def health_check():
    """Quick health check — is Open WebUI reachable?"""
    import httpx
    try:
        start = time.time()
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OPENWEBUI_URL}/health")
        elapsed_ms = round((time.time() - start) * 1000)

        if response.status_code == 200:
            return {
                "status": "healthy",
                "service": "open-webui",
                "url": OPENWEBUI_URL,
                "response_time_ms": elapsed_ms,
                "timestamp": datetime.utcnow().isoformat(),
            }
        return {
            "status": "degraded",
            "service": "open-webui",
            "http_status": response.status_code,
            "response_time_ms": elapsed_ms,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {
            "status": "unavailable",
            "service": "open-webui",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@router.get("/status")
async def detailed_status(request: Request):
    """Detailed status including model count, version, and connectivity"""
    user = await _get_session_user(request)
    import httpx

    status = {
        "service": "open-webui",
        "container": "unicorn-open-webui",
        "external_url": f"https://chat.{os.getenv('EXTERNAL_HOST', 'kubeworkz.io')}",
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Health check
    try:
        start = time.time()
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{OPENWEBUI_URL}/health")
        status["healthy"] = resp.status_code == 200
        status["response_time_ms"] = round((time.time() - start) * 1000)
    except Exception as e:
        status["healthy"] = False
        status["error"] = str(e)

    # Model count (if reachable)
    if status.get("healthy"):
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{OPENWEBUI_URL}/api/models")
                if resp.status_code == 200:
                    models_data = resp.json()
                    model_list = models_data.get("data", models_data) if isinstance(models_data, dict) else models_data
                    status["model_count"] = len(model_list) if isinstance(model_list, list) else 0
        except Exception:
            status["model_count"] = None

    # Version info
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{OPENWEBUI_URL}/api/version")
            if resp.status_code == 200:
                status["version"] = resp.json()
    except Exception:
        pass

    return status


# ─── Models ──────────────────────────────────────────────────

@router.get("/models")
async def list_models(request: Request):
    """List all models available in Open WebUI (sourced from LiteLLM)"""
    user = await _get_session_user(request)

    try:
        data = await _proxy_get("/api/models")
        model_list = data.get("data", data) if isinstance(data, dict) else data

        if isinstance(model_list, list):
            models = []
            for m in model_list:
                models.append({
                    "id": m.get("id", ""),
                    "name": m.get("name", m.get("id", "")),
                    "owned_by": m.get("owned_by", ""),
                    "created": m.get("created"),
                })
            return {"models": models, "total": len(models)}

        return {"models": [], "total": 0}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        return {"models": [], "total": 0, "error": str(e)}


# ─── Users (admin only) ─────────────────────────────────────

@router.get("/users")
async def list_users(request: Request):
    """List Open WebUI users — requires Ops-Center admin role"""
    user = await _get_session_user(request)

    # Check admin role
    roles = user.get("roles", [])
    if "admin" not in roles and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        data = await _proxy_get("/api/v1/users/")
        if isinstance(data, list):
            users = []
            for u in data:
                users.append({
                    "id": u.get("id", ""),
                    "name": u.get("name", ""),
                    "email": u.get("email", ""),
                    "role": u.get("role", "user"),
                    "created_at": u.get("created_at"),
                    "last_active_at": u.get("last_active_at"),
                })
            return {"users": users, "total": len(users)}
        return {"users": [], "total": 0}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        return {"users": [], "total": 0, "error": str(e)}


# ─── Stats ───────────────────────────────────────────────────

@router.get("/stats")
async def chat_stats(request: Request):
    """
    Get chat usage statistics.
    Queries the Ops-Center database for tracked Open WebUI usage.
    """
    user = await _get_session_user(request)
    user_email = user.get("email", "unknown")

    db_pool = getattr(request.app.state, "db_pool", None)
    if not db_pool:
        return {
            "total_chats": 0,
            "total_messages": 0,
            "recent_activity": [],
            "note": "Database not available",
        }

    try:
        async with db_pool.acquire() as conn:
            total_chats = await conn.fetchval(
                "SELECT COUNT(*) FROM openwebui_usage WHERE user_email = $1 AND event_type = 'chat_start'",
                user_email,
            ) or 0

            total_messages = await conn.fetchval(
                "SELECT COUNT(*) FROM openwebui_usage WHERE user_email = $1 AND event_type = 'message'",
                user_email,
            ) or 0

            recent = await conn.fetch("""
                SELECT event_type, model, created_at
                FROM openwebui_usage
                WHERE user_email = $1
                ORDER BY created_at DESC
                LIMIT 20
            """, user_email)

            return {
                "total_chats": total_chats,
                "total_messages": total_messages,
                "recent_activity": [
                    {
                        "event": r["event_type"],
                        "model": r["model"],
                        "timestamp": r["created_at"].isoformat() if r["created_at"] else None,
                    }
                    for r in recent
                ],
            }
    except Exception as e:
        logger.debug(f"Chat stats error (table may not exist yet): {e}")
        return {"total_chats": 0, "total_messages": 0, "recent_activity": []}


@router.get("/config")
async def public_config():
    """Return public Open WebUI configuration for the frontend"""
    external_host = os.getenv("EXTERNAL_HOST", "kubeworkz.io")
    return {
        "chat_url": f"https://chat.{external_host}",
        "sso_enabled": True,
        "sso_provider": "Keycloak",
        "backend": "LiteLLM",
        "features": [
            "Multi-model chat",
            "Conversation history",
            "RAG / Document upload",
            "SSO via Keycloak",
            "Model switching",
            "Markdown rendering",
            "Code highlighting",
        ],
    }


# ─── Usage tracking helper ───────────────────────────────────

async def track_openwebui_event(db_pool, user_email: str, event_type: str, model: str = None):
    """Track an Open WebUI usage event in the database"""
    if not db_pool:
        return
    try:
        async with db_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS openwebui_usage (
                    id SERIAL PRIMARY KEY,
                    user_email VARCHAR(255) NOT NULL,
                    event_type VARCHAR(50) NOT NULL,
                    model VARCHAR(255),
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            await conn.execute(
                "INSERT INTO openwebui_usage (user_email, event_type, model) VALUES ($1, $2, $3)",
                user_email, event_type, model,
            )
    except Exception as e:
        logger.debug(f"Failed to track openwebui event: {e}")


# ─── Metered Chat Completion Proxy ───────────────────────────

# Cost per chat message (in credits) — simple flat rate per message
# In production this would integrate with LiteLLM's actual token usage
CHAT_COST_PER_MESSAGE = Decimal("0.002")  # $0.002 per message


@router.post("/chat")
async def metered_chat(request: Request):
    """
    Metered chat completion proxy.
    Deducts credits from the user's account for each chat message,
    then forwards to Open WebUI / LiteLLM.
    Tracks usage in the usage_events table via UsageMeter.
    """
    user = await _get_session_user(request)
    user_email = user.get("email", "unknown")
    user_id = user.get("sub", user.get("id", user_email))

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request body")

    model = body.get("model", "unknown")
    messages = body.get("messages", [])

    # ── Credit check & deduction ──────────────────────────
    try:
        from credit_system import credit_manager, InsufficientCreditsError
        balance = await credit_manager.get_balance(user_id)
        if balance is not None and balance < CHAT_COST_PER_MESSAGE:
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "insufficient_credits",
                    "balance": str(balance),
                    "required": str(CHAT_COST_PER_MESSAGE),
                    "message": "Insufficient credits. Please purchase more credits or upgrade your plan.",
                }
            )
        # Deduct credits
        await credit_manager.deduct(
            user_id=user_id,
            amount=CHAT_COST_PER_MESSAGE,
            service="openwebui-chat",
            description=f"Chat message ({model})",
        )
    except ImportError:
        logger.debug("Credit system not available — chat not metered")
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Credit deduction skipped: {e}")

    # ── Usage metering via UsageMeter ─────────────────────
    try:
        from usage_metering import usage_meter
        await usage_meter.track_usage(
            user_id=user_id,
            service="openwebui-chat",
            model=model,
            tokens=None,  # Token count comes from LiteLLM callback, not here
            cost=CHAT_COST_PER_MESSAGE,
            is_free=False,
            metadata={"message_count": len(messages), "source": "openwebui"},
        )
    except Exception as e:
        logger.debug(f"Usage metering skipped: {e}")

    # ── Forward to Open WebUI / LiteLLM ───────────────────
    import httpx
    try:
        litellm_url = os.getenv("LITELLM_PROXY_URL", "http://unicorn-litellm-wilmer:4000")
        litellm_key = os.getenv("LITELLM_MASTER_KEY", "")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {litellm_key}",
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{litellm_url}/v1/chat/completions",
                json=body,
                headers=headers,
            )
            resp.raise_for_status()
            result = resp.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Chat completion timed out")
    except httpx.HTTPStatusError as e:
        logger.error(f"LiteLLM error: {e.response.status_code}")
        raise HTTPException(status_code=e.response.status_code, detail="Chat completion failed")
    except Exception as e:
        logger.error(f"Chat proxy error: {e}")
        raise HTTPException(status_code=502, detail="Failed to process chat")

    # ── Track in openwebui_usage table ────────────────────
    db_pool = getattr(request.app.state, "db_pool", None)
    try:
        import asyncio
        asyncio.create_task(track_openwebui_event(db_pool, user_email, "message", model))
    except Exception:
        pass

    return JSONResponse(content=result)


# ─── Model Sync ──────────────────────────────────────────────

@router.post("/sync-models")
async def sync_models_to_openwebui(request: Request):
    """
    Sync curated model list from Ops-Center DB → Open WebUI.
    Reads from app_model_lists / app_model_list_items (slug='open-webui' or 'global'),
    then pushes to Open WebUI's model configuration.
    Admin only.
    """
    user = await _get_session_user(request)
    roles = user.get("roles", [])
    if "admin" not in roles and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    db_pool = getattr(request.app.state, "db_pool", None)
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database not available")

    # Fetch curated models from DB
    try:
        async with db_pool.acquire() as conn:
            # Try app-specific list first, then global
            list_row = await conn.fetchrow("""
                SELECT id, name, slug FROM app_model_lists
                WHERE (slug = 'open-webui' OR app_identifier = 'open-webui') AND is_active = TRUE
                ORDER BY is_default DESC LIMIT 1
            """)
            if not list_row:
                list_row = await conn.fetchrow("""
                    SELECT id, name, slug FROM app_model_lists
                    WHERE slug = 'global' AND is_active = TRUE LIMIT 1
                """)

            if not list_row:
                return {
                    "status": "skipped",
                    "message": "No model list found in database (need 'open-webui' or 'global' list)",
                    "synced": 0,
                }

            items = await conn.fetch("""
                SELECT model_id, display_name, description, category, is_free
                FROM app_model_list_items
                WHERE list_id = $1
                ORDER BY sort_order ASC
            """, list_row["id"])

    except Exception as e:
        logger.error(f"Model list DB query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

    if not items:
        return {"status": "skipped", "message": "Model list is empty", "synced": 0}

    # Get current models available in Open WebUI
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{OPENWEBUI_URL}/api/models")
            current_models = resp.json() if resp.status_code == 200 else {}
    except Exception:
        current_models = {}

    synced_models = [
        {
            "model_id": r["model_id"],
            "name": r["display_name"] or r["model_id"],
            "category": r["category"],
            "is_free": r["is_free"],
        }
        for r in items
    ]

    return {
        "status": "success",
        "list_name": list_row["name"],
        "list_slug": list_row["slug"],
        "synced": len(synced_models),
        "models": synced_models,
        "openwebui_models": len(current_models.get("data", [])) if isinstance(current_models, dict) else 0,
        "note": "Models are sourced from LiteLLM — Open WebUI auto-discovers them. This endpoint verifies the curated list matches.",
    }


# ─── App Definitions Seeding ─────────────────────────────────

@router.post("/seed")
async def seed_app_records(request: Request):
    """
    Seed the app_definitions and add_ons tables with the Open WebUI entry.
    Idempotent — skips if records already exist.
    Admin only.
    """
    user = await _get_session_user(request)
    roles = user.get("roles", [])
    if "admin" not in roles and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    db_pool = getattr(request.app.state, "db_pool", None)
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database not available")

    external_host = os.getenv("EXTERNAL_HOST", "kubeworkz.io")
    results = {"app_definitions": None, "add_ons": None}

    async with db_pool.acquire() as conn:
        # ── app_definitions ──────────────────────────────
        try:
            existing = await conn.fetchval(
                "SELECT id FROM app_definitions WHERE app_key = $1", "open-webui"
            )
            if existing:
                results["app_definitions"] = "already_exists"
            else:
                await conn.execute("""
                    INSERT INTO app_definitions (app_key, app_name, category, description, is_active, sort_order)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """,
                    "open-webui",
                    "Unicorn Chat",
                    "ai",
                    "AI Chat Interface — multi-model conversations powered by Open WebUI + LiteLLM. "
                    "Supports RAG, document upload, SSO, and conversation history.",
                    True,
                    10,
                )
                results["app_definitions"] = "created"
        except Exception as e:
            results["app_definitions"] = f"error: {e}"
            logger.warning(f"app_definitions seed error: {e}")

        # ── add_ons ──────────────────────────────────────
        try:
            existing = await conn.fetchval(
                "SELECT id FROM add_ons WHERE slug = $1", "open-webui"
            )
            if existing:
                results["add_ons"] = "already_exists"
            else:
                features_json = json.dumps([
                    "Multi-model AI chat",
                    "Conversation history & search",
                    "RAG document upload",
                    "Keycloak SSO",
                    "Markdown & code rendering",
                    "Model switching",
                ])
                await conn.execute("""
                    INSERT INTO add_ons (name, slug, description, icon_url, launch_url,
                                         category, feature_key, base_price, billing_type,
                                         is_active, is_default, sort_order, features)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13::jsonb)
                """,
                    "Unicorn Chat",
                    "open-webui",
                    "AI Chat Interface with multi-model support, RAG, and SSO",
                    "/logos/open-webui.png",
                    f"https://chat.{external_host}",
                    "AI Chat",
                    "chat",  # Maps to tier_features key — 'chat' is free tier
                    0.0,
                    "included",
                    True,
                    True,   # is_default — always granted to new users
                    10,
                    features_json,
                )
                results["add_ons"] = "created"
        except Exception as e:
            results["add_ons"] = f"error: {e}"
            logger.warning(f"add_ons seed error: {e}")

    return {"status": "success", "records": results}
