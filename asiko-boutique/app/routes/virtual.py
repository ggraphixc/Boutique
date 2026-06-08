# ASIKO Boutique — Virtual Atelier Routes
# 3D Showroom & Dressing Room experience backend.
# Database-backed: products.model_3d_url, morph_target_index, apparel_layer_depth,
# model_usdz_url, product_variants for shader metadata.

from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.routing import Route

from app.core import templates

# Procedural fallback forms for missing/corrupt 3D assets
_PROCEDURAL_DEFAULTS = {
    "dress": {
        "mesh": "dress_form",
        "label": "Draped Silhouette",
        "fallback_color": "#0D2A22",
    },
    "blazer": {
        "mesh": "blazer_form",
        "label": "Structured Shoulder",
        "fallback_color": "#1a1a2e",
    },
    "trouser": {
        "mesh": "trouser_form",
        "label": "Tapered Column",
        "fallback_color": "#e8d5c0",
    },
    "top": {
        "mesh": "top_form",
        "label": "Fitted Shell",
        "fallback_color": "#d4af37",
    },
}

VALID_GENDERS = {"male", "female", "unisex"}


def _resolve_mesh(ref: str | None) -> str:
    """Map null/missing mesh_node_identifier to procedural fallback."""
    if not ref:
        return "dress_form"
    return ref


def _resolve_color(hex_val: str | None, fallback: str = "#0D2A22") -> str:
    """Validate hex color or return safe default."""
    if not hex_val or not hex_val.startswith("#") or len(hex_val) != 7:
        return fallback
    return hex_val


async def virtual_experience(request: Request) -> HTMLResponse:
    """Render the 3D Virtual Atelier experience page."""
    cart = request.session.get("cart", {"item_count": 0, "total": 0.0, "lines": []})

    saved_measurements = request.session.get("atelier_dimensions", None)

    context = {
        "request": request,
        "cart": cart,
        "saved_measurements": saved_measurements,
    }
    return templates.TemplateResponse(
        request, "virtual_experience.html", context,
    )


async def showroom_items_fragment(request: Request) -> HTMLResponse:
    """
    HTMX fragment: 3D showroom product cards with GLTF model metadata.
    Queries products.model_3d_url and variant shader columns from the database.
    Falls back to procedural geometry references for missing assets.
    """
    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        records = await conn.fetch(
            """
            SELECT p.id, p.name, p.model_3d_url, p.price,
                   v.id AS variant_id, v.size, v.color,
                   v.mesh_node_identifier, v.custom_shader_color
            FROM products p
            LEFT JOIN product_variants v ON v.product_id = p.id
            WHERE p.model_3d_url IS NOT NULL
            ORDER BY p.name, v.size
            LIMIT 20
            """
        )

    if not records:
        return HTMLResponse(
            "<div class='text-xs font-mono text-neutral-400 p-4'>"
            "No 3D assets loaded in ledger.</div>"
        )

    cards_html = ""
    for r in records:
        color_hex = _resolve_color(r["custom_shader_color"])
        mesh_ref = _resolve_mesh(r["mesh_node_identifier"])
        model_url = r["model_3d_url"]
        variant_id = str(r["variant_id"]) if r["variant_id"] else ""
        product_id = str(r["id"])
        price_val = float(r["price"]) if r["price"] else 0

        cards_html += f"""
        <div class="glass-panel rounded-xl p-4 flex items-center justify-between
                    hover:shadow-md transition-all cursor-pointer
                    border border-[#D4AF37]/10"
             @click="$dispatch('load-showroom-model', {{
                 modelUrl: '{model_url}',
                 color: '{color_hex}',
                 mesh: '{mesh_ref}',
                 variantId: '{variant_id}',
                 productId: '{product_id}'
             }})"
             role="button"
             tabindex="0"
             aria-label="View {r['name']}">
            <div>
                <h4 class="text-sm font-medium text-[#0D2A22]">{r['name']}</h4>
                <p class="text-[10px] font-mono text-neutral-400 uppercase tracking-wider mt-0.5">
                    {r['color']} &middot; Size {r['size']}
                </p>
                <p class="text-[10px] text-neutral-500 font-mono mt-0.5">
                    Mesh: {mesh_ref}
                </p>
            </div>
            <div class="text-right">
                <span class="font-mono text-sm text-[#0D2A22]">&curren;{price_val:,.0f}</span>
            </div>
        </div>
        """

    html = f"""
    <div class="space-y-3" x-data>
        {cards_html}
    </div>
    """
    return HTMLResponse(html)


async def capsule_layers_fragment(request: Request) -> HTMLResponse:
    """
    GET /api/virtual/capsule-layers?capsule_id=N&gender=female
    Resolves a full style capsule look bundle sorted by priority_order.
    Accepts gender_axis param for future skeleton fit filtering.
    Returns pre-compiled HTML fragments with inline Alpine.js dispatch hooks.
    """
    capsule_id = request.query_params.get("capsule_id")
    if not capsule_id:
        return HTMLResponse(
            "<div class='text-xs font-mono text-[#EF4444] p-4'>"
            "Missing capsule_id parameter.</div>",
            status_code=400,
        )

    # Defensive fallback chain: explicit query param → session value → "female".
    # .get() with a default only handles *missing* keys; we must also guard against
    # keys that exist but are empty strings (which would otherwise propagate "" down
    # to the frontend loader and break the skeleton fit filter).
    _query_gender = request.query_params.get("gender")
    _session_gender = request.session.get("preferred_avatar_axis")
    if _query_gender and _query_gender.strip():
        gender_axis = _query_gender.strip()
    elif _session_gender and _session_gender.strip():
        gender_axis = _session_gender.strip()
    else:
        gender_axis = "female"

    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        records = await conn.fetch(
            """
            SELECT p.id, p.name, p.model_3d_url, p.price,
                   v.id AS variant_id, v.size, v.color,
                   v.mesh_node_identifier, v.custom_shader_color,
                   a.priority_order, a.is_required_for_look
            FROM asiko_capsule_assignments a
            JOIN products p ON p.id = a.product_id
            LEFT JOIN product_variants v ON v.product_id = p.id
            WHERE a.capsule_id = $1
              AND v.id IS NOT NULL
            ORDER BY a.priority_order ASC
            LIMIT 30
            """,
            int(capsule_id),
        )

    if not records:
        return HTMLResponse(
            "<div class='text-xs font-mono text-neutral-400 p-4'>"
            "No capsule layers found for this look.</div>"
        )

    layers_html = ""
    for idx, r in enumerate(records):
        color_hex = _resolve_color(r["custom_shader_color"])
        model_url = r["model_3d_url"]
        variant_id = str(r["variant_id"])
        product_id = str(r["id"])
        is_required = r["is_required_for_look"]
        priority = r["priority_order"] or 0

        if not model_url:
            mesh_ref = _resolve_mesh(r["mesh_node_identifier"])
            procedural_hint = f" Procedural: {mesh_ref}"
        else:
            mesh_ref = _resolve_mesh(r["mesh_node_identifier"])
            procedural_hint = ""

        required_badge = (
            '<span class="text-[9px] font-mono uppercase tracking-widest text-[#D4AF37]">Required</span>'
            if is_required else ""
        )

        layers_html += f"""
        <div class="glass-panel rounded-xl p-4 flex items-center justify-between
                    hover:shadow-md transition-all cursor-pointer
                    border border-[#D4AF37]/10 animate-fade-in"
             style="animation-delay: {idx * 80}ms"
             @click="$dispatch('layer-capsule-mesh', {{
                 layerIndex: {idx},
                 modelUrl: '{model_url or ''}',
                 color: '{color_hex}',
                 mesh: '{mesh_ref}',
                 variantId: '{variant_id}',
                 productId: '{product_id}',
                 priority: {priority},
                 isRequired: {'true' if is_required else 'false'}
             }})"
             role="button"
             tabindex="0"
             aria-label="Layer {idx + 1}: {r['name']}">
            <div class="flex items-center gap-3">
                <div class="w-8 h-8 rounded-lg bg-[#0D2A22]/5 flex items-center justify-center
                            text-[10px] font-mono text-[#0D2A22]/40">
                    L{idx + 1}
                </div>
                <div>
                    <h4 class="text-sm font-medium text-[#0D2A22]">{r['name']}</h4>
                    <p class="text-[10px] font-mono text-neutral-400 uppercase tracking-wider mt-0.5">
                        {r['color']} &middot; Size {r['size']}{procedural_hint}
                    </p>
                </div>
            </div>
            <div class="text-right flex flex-col items-end gap-1">
                <span class="font-mono text-xs text-[#0D2A22]">&curren;{float(r['price']):,.0f}</span>
                {required_badge}
            </div>
        </div>
        """

    html = f"""
    <div class="space-y-2" x-data>
        <div class="px-4 py-2 border-b border-[#0D2A22]/5">
            <h3 class="text-[10px] font-mono uppercase tracking-[0.2em] text-[#0D2A22]">
                Capsule Layers ({len(records)} items &middot; {gender_axis} fit)
            </h3>
        </div>
        {layers_html}
    </div>
    """
    return HTMLResponse(html)


routes = [
    Route("/virtual-experience", endpoint=virtual_experience, methods=["GET"]),
    Route("/api/virtual/showroom-items", endpoint=showroom_items_fragment, methods=["GET"]),
    Route("/api/virtual/capsule-layers", endpoint=capsule_layers_fragment, methods=["GET"]),
]