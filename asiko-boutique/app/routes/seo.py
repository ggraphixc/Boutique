# ASIKO Boutique - SEO Routes (sitemap.xml, robots.txt, structured data)

from __future__ import annotations
import json, logging
from datetime import datetime
from starlette.requests import Request
from starlette.responses import PlainTextResponse, JSONResponse
from starlette.routing import Route

logger = logging.getLogger("asiko.seo")


async def sitemap_xml(request: Request) -> PlainTextResponse:
    """GET /sitemap.xml — Dynamic sitemap for search engines."""
    pool = request.app.state.db_pool
    base = str(request.base_url).rstrip("/")
    urls = [f"{base}/", f"{base}/faq", f"{base}/lookbook", f"{base}/shipping", f"{base}/size-guide", f"{base}/terms", f"{base}/privacy"]

    try:
        async with pool.acquire() as conn:
            # Products
            rows = await conn.fetch("SELECT id, updated_at FROM products WHERE is_active = TRUE ORDER BY updated_at DESC LIMIT 500")
            for r in rows:
                lastmod = r["updated_at"].strftime("%Y-%m-%d") if r["updated_at"] else datetime.now().strftime("%Y-%m-%d")
                urls.append(f"{base}/product/{r['id']}")

            # Blog posts
            rows = await conn.fetch("SELECT cp.slug, cp.updated_at FROM blog_posts bp JOIN custom_pages cp ON cp.id = bp.page_id WHERE bp.is_published = TRUE LIMIT 100")
            for r in rows:
                urls.append(f"{base}/blog/{r['slug']}")

            # Custom pages
            rows = await conn.fetch("SELECT slug, updated_at FROM custom_pages WHERE is_live = TRUE AND page_type != 'blog' LIMIT 100")
            for r in rows:
                urls.append(f"{base}/page/{r['slug']}")

    except Exception as exc:
        logger.warning("[seo] sitemap query failed: %s", exc)

    xml_parts = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url in urls:
        xml_parts.append(f"  <url><loc>{url}</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>")
    xml_parts.append("</urlset>")
    return PlainTextResponse("\n".join(xml_parts), media_type="application/xml")


async def robots_txt(request: Request) -> PlainTextResponse:
    """GET /robots.txt — Robots directive for crawlers."""
    pool = request.app.state.db_pool
    base = str(request.base_url).rstrip("/")
    content = f"""User-agent: *
Allow: /
Disallow: /admin/
Disallow: /api/
Disallow: /checkout
Disallow: /cart

Sitemap: {base}/sitemap.xml
"""
    return PlainTextResponse(content, media_type="text/plain")


async def structured_data_product(request: Request, product: dict, settings: dict) -> dict:
    """Generate Product JSON-LD for a product page."""
    if not settings.get("aeo_product_schema"):
        return {}
    return {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": product.get("name", ""),
        "description": product.get("description", ""),
        "image": product.get("base_image", ""),
        "brand": {"@type": "Brand", "name": settings.get("brand_name", "ASIKO")},
        "offers": {
            "@type": "Offer",
            "price": product.get("price", 0),
            "priceCurrency": settings.get("brand_currency_code", "NGN"),
            "availability": "https://schema.org/InStock" if product.get("stock_quantity", 0) > 0 else "https://schema.org/OutOfStock",
            "seller": {"@type": "Organization", "name": settings.get("brand_name", "ASIKO")},
        },
    }


async def structured_data_faq(request: Request, settings: dict) -> dict:
    """Generate FAQ JSON-LD for the FAQ page."""
    if not settings.get("aeo_faq_schema"):
        return {}
    pool = request.app.state.db_pool
    faqs = []
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT question, answer FROM ai_training_data WHERE is_active = TRUE AND category = 'faq' ORDER BY sort_order LIMIT 20")
            for r in rows:
                faqs.append({"@type": "Question", "name": r["question"], "acceptedAnswer": {"@type": "Answer", "text": r["answer"]}})
    except Exception:
        pass
    if not faqs:
        return {}
    return {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": faqs}


async def structured_data_local_business(request: Request, settings: dict) -> dict:
    """Generate LocalBusiness JSON-LD for GEO."""
    if not settings.get("geo_enabled"):
        return {}
    geo = settings.get("geo_local_business", {})
    if isinstance(geo, str):
        try:
            geo = json.loads(geo) if geo else {}
        except Exception:
            geo = {}
    return {
        "@context": "https://schema.org",
        "@type": "ClothingStore",
        "name": settings.get("brand_name", "ASIKO Boutique"),
        "description": settings.get("brand_tagline", "Authentic Nigerian Fashion"),
        "url": str(request.base_url).rstrip("/"),
        "telephone": geo.get("phone", settings.get("phone", "")),
        "address": {
            "@type": "PostalAddress",
            "streetAddress": geo.get("street", ""),
            "addressLocality": geo.get("city", "Lagos"),
            "addressRegion": geo.get("region", "Lagos"),
            "addressCountry": geo.get("country", "NG"),
            "postalCode": geo.get("postal", ""),
        },
        "geo": {
            "@type": "GeoCoordinates",
            "latitude": geo.get("lat", 6.5244),
            "longitude": geo.get("lng", 3.3792),
        },
        "sameAs": [],
    }


routes = [
    Route("/sitemap.xml", endpoint=sitemap_xml, methods=["GET"]),
    Route("/robots.txt", endpoint=robots_txt, methods=["GET"]),
]
