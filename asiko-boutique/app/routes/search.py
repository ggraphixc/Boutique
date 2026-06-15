# ASIKO Boutique - AI-Powered Search Engine
# Provides unified search across products, FAQs, pages, and AI-assisted answers.

from __future__ import annotations
import json, logging
from typing import Any, Dict, List
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

logger = logging.getLogger("asiko.search")


async def search_endpoint(request: Request) -> JSONResponse:
    """GET /api/search?q=query — Unified search across products, FAQs, pages with AI assist."""
    pool = request.app.state.db_pool
    q = request.query_params.get("q", "").strip()
    if not q:
        return JSONResponse({"results": [], "ai_answer": ""})

    results: List[Dict[str, Any]] = []
    q_lower = q.lower()
    q_words = q_lower.split()

    try:
        async with pool.acquire() as conn:
            # 1. Search products (name, description)
            try:
                conditions = []
                params = []
                for i, word in enumerate(q_words):
                    conditions.append(f"(p.name ILIKE ${i*2+1} OR p.description ILIKE ${i*2+2})")
                    params.extend([f"%{word}%", f"%{word}%"])
                where = " AND ".join(conditions)
                rows = await conn.fetch(
                    f"SELECT p.id, p.name, p.price, p.base_image, c.name AS category_name "
                    f"FROM products p LEFT JOIN categories c ON c.id = p.category_id "
                    f"WHERE {where} ORDER BY p.name LIMIT 6",
                    *params
                )
                for r in rows:
                    results.append({
                        "type": "product",
                        "id": str(r["id"]),
                        "title": r["name"],
                        "subtitle": f"₦{float(r['price']):,.0f} — {r['category_name'] or 'Fashion'}",
                        "image": r.get("base_image", ""),
                        "url": f"/product/{r['id']}",
                    })
            except Exception as exc:
                logger.warning("[search] product search failed: %s", exc)

            # 2. Search FAQ pages (from custom_pages with page_type='faq')
            try:
                rows = await conn.fetch(
                    "SELECT title, slug, excerpt, body_html FROM custom_pages "
                    "WHERE is_live = TRUE AND (title ILIKE $1 OR body_html ILIKE $1) LIMIT 5",
                    f"%{q}%"
                )
                for r in rows:
                    results.append({
                        "type": "page",
                        "title": r["title"],
                        "subtitle": (r["excerpt"] or "")[:120],
                        "url": f"/page/{r['slug']}",
                    })
            except Exception:
                pass

            # 3. Search blog posts
            try:
                rows = await conn.fetch(
                    "SELECT cp.title, cp.slug, cp.excerpt FROM blog_posts bp "
                    "JOIN custom_pages cp ON cp.id = bp.page_id "
                    "WHERE bp.is_published = TRUE AND (cp.title ILIKE $1 OR cp.excerpt ILIKE $1) LIMIT 3",
                    f"%{q}%"
                )
                for r in rows:
                    results.append({
                        "type": "blog",
                        "title": r["title"],
                        "subtitle": (r["excerpt"] or "")[:120],
                        "url": f"/blog/{r['slug']}",
                    })
            except Exception:
                pass

            # 4. Search AI training data for direct answers
            ai_answer = ""
            try:
                row = await conn.fetchrow(
                    "SELECT answer FROM ai_training_data "
                    "WHERE is_active = TRUE AND (question ILIKE $1 OR question ILIKE $2) LIMIT 1",
                    f"%{q}%", f"%{q_lower}%"
                )
                if row:
                    ai_answer = row["answer"]
            except Exception:
                pass

            # 5. If no results and AI provider is configured, ask the AI
            if not results and not ai_answer:
                try:
                    from app.settings_service import get_settings
                    settings = await get_settings(pool)
                    if settings.get("ai_api_key"):
                        from app.fashion_ai import _get_provider_config
                        config = _get_provider_config(settings=settings)
                        if config:
                            import httpx
                            headers = {}
                            if config["provider"] == "openrouter":
                                headers = {"Authorization": f"Bearer {config['api_key']}", "HTTP-Referer": "https://asikoboutique.com"}
                            elif config["provider"] == "openai":
                                headers = {"Authorization": f"Bearer {config['api_key']}"}

                            system_prompt = (
                                "You are ASIKO Boutique's fashion assistant. Answer questions about Nigerian fashion, "
                                "styling, products, sizing, delivery, and returns. Be helpful and concise. "
                                "If the question is about a specific product, suggest browsing the shop."
                            )
                            payload = {
                                "model": config["model"],
                                "messages": [
                                    {"role": "system", "content": system_prompt},
                                    {"role": "user", "content": q}
                                ],
                                "max_tokens": 300,
                            }
                            async with httpx.AsyncClient(timeout=15) as client:
                                resp = await client.post(config["url"], json=payload, headers=headers)
                                if resp.status_code == 200:
                                    data = resp.json()
                                    ai_answer = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                except Exception as exc:
                    logger.warning("[search] AI assist failed: %s", exc)

    except Exception as exc:
        logger.error("[search] search failed: %s", exc)

    return JSONResponse({"results": results, "ai_answer": ai_answer, "query": q})


async def search_page(request: Request) -> JSONResponse:
    """GET /search — Redirect to homepage with search query."""
    from starlette.responses import RedirectResponse
    q = request.query_params.get("q", "").strip()
    return RedirectResponse(f"/?q={q}" if q else "/", status_code=302)


routes = [
    Route("/api/search", endpoint=search_endpoint, methods=["GET"]),
    Route("/search", endpoint=search_page, methods=["GET"]),
]
