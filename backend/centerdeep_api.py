"""
Center-Deep Search API - Privacy-focused metasearch proxy
Proxies search requests to SearXNG with auth, tier gating, and usage metering
"""

import os
import logging
import time
from typing import Optional, Dict, Any
from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/search", tags=["Center-Deep Search"])

# SearXNG internal URL (container-to-container)
SEARXNG_URL = os.getenv("SEARXNG_URL", "http://unicorn-searxng:8080")

# Search categories
VALID_CATEGORIES = [
    "general", "images", "videos", "news", "music",
    "science", "files", "it", "social media", "map"
]


async def get_search_user(request: Request) -> Dict[str, Any]:
    """Get authenticated user from session"""
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
        logger.error(f"Auth error in search: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")


@router.get("")
async def search(
    request: Request,
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    categories: str = Query("general", description="Comma-separated categories"),
    page: int = Query(1, ge=1, le=50, description="Page number"),
    language: str = Query("en", description="Search language"),
    time_range: Optional[str] = Query(None, description="Time filter: day, week, month, year"),
    safesearch: int = Query(0, ge=0, le=2, description="Safe search: 0=off, 1=moderate, 2=strict"),
):
    """
    Search across 70+ engines via SearXNG.
    Returns deduplicated, ranked results from multiple search providers.
    """
    user = await get_search_user(request)
    user_email = user.get("email", "unknown")

    # Validate categories
    cat_list = [c.strip() for c in categories.split(",")]
    for cat in cat_list:
        if cat and cat not in VALID_CATEGORIES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid category: {cat}. Valid: {', '.join(VALID_CATEGORIES)}"
            )

    # Build SearXNG request
    import httpx

    params = {
        "q": q,
        "format": "json",
        "categories": categories,
        "pageno": page,
        "language": language,
        "safesearch": safesearch,
    }
    if time_range:
        params["time_range"] = time_range

    try:
        start_time = time.time()
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(f"{SEARXNG_URL}/search", params=params)
            response.raise_for_status()

        elapsed_ms = round((time.time() - start_time) * 1000)
        data = response.json()

        results = data.get("results", [])
        suggestions = data.get("suggestions", [])
        infoboxes = data.get("infoboxes", [])
        answers = data.get("answers", [])

        # Collect engine stats
        engines_used = set()
        for r in results:
            for e in r.get("engines", []):
                engines_used.add(e)

        # Format results for frontend
        formatted_results = []
        for i, r in enumerate(results):
            formatted_results.append({
                "id": i + 1,
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": r.get("content", ""),
                "engine": r.get("engines", ["unknown"])[0] if r.get("engines") else "unknown",
                "engines": r.get("engines", []),
                "score": r.get("score", 0),
                "category": r.get("category", "general"),
                "thumbnail": r.get("thumbnail"),
                "img_src": r.get("img_src"),
                "publishedDate": r.get("publishedDate"),
                "metadata": r.get("metadata"),
            })

        # Log search for analytics
        logger.info(f"Search: user={user_email} q='{q}' cat={categories} "
                     f"results={len(results)} engines={len(engines_used)} time={elapsed_ms}ms")

        # Track usage (async, don't block response)
        try:
            db_pool = request.app.state.db_pool
            if db_pool:
                import asyncio
                asyncio.create_task(_track_search_usage(db_pool, user_email, q, categories, len(results)))
        except Exception:
            pass

        return JSONResponse(content={
            "query": q,
            "results": formatted_results,
            "suggestions": list(suggestions) if suggestions else [],
            "answers": list(answers) if answers else [],
            "infoboxes": infoboxes,
            "total_results": len(formatted_results),
            "page": page,
            "categories": cat_list,
            "engines_used": sorted(engines_used),
            "response_time_ms": elapsed_ms,
        })

    except httpx.TimeoutException:
        logger.warning(f"Search timeout: q='{q}' categories={categories}")
        raise HTTPException(status_code=504, detail="Search timed out. Please try again.")
    except httpx.HTTPStatusError as e:
        logger.error(f"SearXNG error: {e.response.status_code} - {e.response.text[:200]}")
        raise HTTPException(status_code=502, detail="Search service error")
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail="Search failed")


@router.get("/suggestions")
async def get_suggestions(
    request: Request,
    q: str = Query(..., min_length=1, max_length=200, description="Query for suggestions"),
):
    """Get autocomplete suggestions for a search query"""
    user = await get_search_user(request)

    import httpx
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{SEARXNG_URL}/autocompleter",
                params={"q": q}
            )
            if response.status_code == 200:
                return response.json()
            return []
    except Exception as e:
        logger.debug(f"Autocomplete error: {e}")
        return []


@router.get("/engines")
async def list_engines(request: Request):
    """List available search engines and their status"""
    user = await get_search_user(request)

    import httpx
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{SEARXNG_URL}/config")
            if response.status_code == 200:
                config = response.json()
                engines = []
                for name, info in config.get("engines", {}).items():
                    engines.append({
                        "name": name,
                        "categories": info.get("categories", []),
                        "language_support": info.get("language_support", False),
                        "paging": info.get("paging", False),
                        "safesearch": info.get("safesearch", False),
                        "time_range_support": info.get("time_range_support", False),
                        "shortcut": info.get("shortcut", ""),
                    })
                return {"engines": engines, "total": len(engines)}
            return {"engines": [], "total": 0}
    except Exception as e:
        logger.error(f"Engine list error: {e}")
        return {"engines": [], "total": 0}


@router.get("/stats")
async def search_stats(request: Request):
    """Get search usage statistics for the current user"""
    user = await get_search_user(request)
    user_email = user.get("email", "unknown")

    db_pool = request.app.state.db_pool
    if not db_pool:
        return {"total_searches": 0, "recent_searches": []}

    try:
        async with db_pool.acquire() as conn:
            # Total searches
            total = await conn.fetchval(
                "SELECT COUNT(*) FROM search_history WHERE user_email = $1",
                user_email
            )

            # Recent searches (last 20)
            recent = await conn.fetch("""
                SELECT query, categories, result_count, created_at
                FROM search_history
                WHERE user_email = $1
                ORDER BY created_at DESC
                LIMIT 20
            """, user_email)

            return {
                "total_searches": total or 0,
                "recent_searches": [
                    {
                        "query": r["query"],
                        "categories": r["categories"],
                        "result_count": r["result_count"],
                        "timestamp": r["created_at"].isoformat() if r["created_at"] else None,
                    }
                    for r in recent
                ]
            }
    except Exception as e:
        logger.debug(f"Search stats error (table may not exist yet): {e}")
        return {"total_searches": 0, "recent_searches": []}


async def _track_search_usage(db_pool, user_email: str, query: str, categories: str, result_count: int):
    """Track search usage in the database"""
    try:
        async with db_pool.acquire() as conn:
            # Create table if not exists
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS search_history (
                    id SERIAL PRIMARY KEY,
                    user_email VARCHAR(255) NOT NULL,
                    query TEXT NOT NULL,
                    categories VARCHAR(255),
                    result_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            await conn.execute(
                "INSERT INTO search_history (user_email, query, categories, result_count) VALUES ($1, $2, $3, $4)",
                user_email, query, categories, result_count
            )
    except Exception as e:
        logger.debug(f"Failed to track search: {e}")
