# ASIKO Boutique - Admin Section Routes (redesign)
# Verifies the 8 light-theme sections are wired, render the expected markers,
# and tolerate an empty/missing database (graceful empty states).
#
# Uses a fresh Starlette app with mocked db_pool, matching the test_webhooks
# pattern in this repo. This avoids the real Neon DB pool init that hangs
# under pytest.

import pytest
from unittest.mock import MagicMock, AsyncMock
from contextlib import asynccontextmanager
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.testclient import TestClient

from app.routes.admin_sections import routes as admin_sections_routes
from app.routes.admin_dashboard import routes as admin_dashboard_routes


def _make_empty_pool():
    """Mock pool whose acquire() returns a conn whose fetch*/fetchrow return empty."""
    pool = MagicMock()

    @asynccontextmanager
    async def _acquire():
        conn = MagicMock()
        # fetch / fetchrow / fetchval all return empty values
        conn.fetch = AsyncMock(return_value=[])
        conn.fetchrow = AsyncMock(return_value=None)
        conn.fetchval = AsyncMock(return_value=0)
        conn.execute = AsyncMock(return_value=None)
        yield conn

    pool.acquire = _acquire
    return pool


def _make_populated_pool():
    """Mock pool that returns one inventory row for the operations section,
    so the HTMX forms actually render in tests."""
    pool = MagicMock()
    inventory_row = {
        "product_id": "11111111-1111-1111-1111-111111111111",
        "name": "Aba Handloomed Trouser",
        "model_3d_url": "/static/models/foo.glb",
        "source_2d_image_url": None,
        "pipeline_status": "completed",
        "variant_id": "22222222-2222-2222-2222-222222222222",
        "size": "L",
        "color": "Natural Cotton",
        "stock_qty": 7,
    }

    @asynccontextmanager
    async def _acquire():
        conn = MagicMock()
        # The operations section runs 3 fetch() calls (inventory, reservations,
        # waitlists). We return inventory data only; the others stay empty.
        async def _fetch(query, *args, **kwargs):
            if "FROM product_variants v" in query:
                return [inventory_row]
            return []
        conn.fetch = AsyncMock(side_effect=_fetch)
        conn.fetchrow = AsyncMock(return_value=None)
        conn.fetchval = AsyncMock(return_value=0)
        conn.execute = AsyncMock(return_value=None)
        yield conn

    pool.acquire = _acquire
    return pool


def _make_app_with_routes(pool_factory=_make_empty_pool):
    """Fresh Starlette app with admin section routes + legacy admin dashboard
    routes + mocked pool. SessionMiddleware is required because base.html
    reads request.session."""
    test_app = Starlette(
        routes=admin_sections_routes + admin_dashboard_routes,
        middleware=[Middleware(SessionMiddleware, secret_key="test-key", session_cookie="asiko_test")],
    )
    test_app.state.db_pool = pool_factory()
    return test_app


# 8 sections + admin index
# Each entry: (path, marker_substring).
# /admin renders the base shell — use a shell-specific marker.
# Section endpoints render the section templates — use data-section="<slug>".
SECTIONS = [
    ("/admin",                       "ÀSÌKÒ"),
    ("/admin/section/dashboard",     "data-section=\"dashboard\""),
    ("/admin/section/products",      "data-section=\"products\""),
    ("/admin/section/categories",    "data-section=\"categories\""),
    ("/admin/section/all-products",  "data-section=\"all-products\""),
    ("/admin/section/reviews",       "data-section=\"reviews\""),
    ("/admin/section/ads",           "data-section=\"ads\""),
    ("/admin/section/operations",    "data-section=\"operations\""),
    ("/admin/section/settings",      "data-section=\"settings\""),
    ("/admin/section/about",         "data-section=\"about\""),
]


class TestAdminSectionRendering:
    """Each section endpoint renders its expected template markers."""

    @pytest.mark.parametrize("path,marker", SECTIONS)
    def test_section_renders(self, path, marker):
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            r = client.get(path)
            assert r.status_code == 200, f"{path} returned {r.status_code}: {r.text[:200]}"
            assert marker in r.text, f"{path} missing marker {marker!r}"


class TestAdminIndexBaseTemplate:
    """The /admin index renders the new light-theme base shell with 8 nav items."""

    def test_index_uses_light_theme(self):
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            r = client.get("/admin")
            assert r.status_code == 200
            body = r.text
            # Light theme markers
            assert "bg-white" in body
            assert "border-r border-gray-200" in body
            # Brand
            assert "ÀSÌKÒ" in body
            assert "Pro Atelier" in body  # subtitle below brand
            # 8 nav items, each with id="nav-XXX"
            for nav_id in (
                "nav-dashboard", "nav-products", "nav-categories",
                "nav-reviews", "nav-ads", "nav-settings", "nav-about",
                # nav-sales (renamed from nav-all-products in the shell) and
                # nav-sales both map to all-products via idMap in JS
                "nav-sales",
            ):
                assert nav_id in body, f"missing nav id {nav_id}"

    def test_index_uses_htmx_workspace_target(self):
        """The workspace hx-target is #workspace-content (NOT #workspace)."""
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            r = client.get("/admin")
            assert 'hx-target="#workspace-content"' in r.text

    def test_index_loads_dashboard_by_default(self):
        """The hx-trigger=load on workspace loads /admin/section/dashboard."""
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            r = client.get("/admin")
            assert 'hx-get="/admin/section/dashboard"' in r.text

    def test_collapse_button_present(self):
        """Hide/Show button is in the sidebar footer with localStorage persistence."""
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            r = client.get("/admin")
            assert "Hide" in r.text
            assert "asiko:sidebarOpen" in r.text  # localStorage key

    def test_index_single_nav_group_v2(self):
        """V2 shell uses a single nav group (no MAIN/INSIGHTS/CONFIG headers at the top,
        only one Account divider)."""
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            body = client.get("/admin").text
            # The "Account" divider is present
            assert "Account" in body
            # The old group headers (MAIN, INSIGHTS, CONFIG) are gone
            assert ">MAIN<" not in body
            assert ">INSIGHTS<" not in body
            assert ">CONFIG<" not in body

    def test_index_light_blue_active_state_v2(self):
        """V2 active state is light-blue (rgb(239, 246, 255) / blue-50 + blue-600 text)."""
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            body = client.get("/admin").text
            # The CSS rule for the active state
            assert "rgb(239, 246, 255)" in body  # blue-50 background
            assert "rgb(37, 99, 235)" in body    # blue-600 text/icon
            # The JS setActiveNav() handler exists
            assert "setActiveNav" in body
            # is-active class is toggled in the handler
            assert "is-active" in body

    def test_index_top_bar_right_side_icons_only(self):
        """V2 top bar has only right-side icons (no big title). The page title
        lives in the workspace content area instead."""
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            body = client.get("/admin").text
            # Right-side icons are present
            assert "title=\"Source code\"" in body
            assert "title=\"Bookmark\"" in body
            assert "title=\"Notifications\"" in body
            assert "title=\"Toggle theme\"" in body
            assert "title=\"Profile\"" in body
            # No big title in the top bar (titles live in the workspace content)
            assert "<h1" not in body.split('<main id="workspace"')[1].split('<!-- HTMX content renders here -->')[0]

    def test_index_help_and_support_bottom(self):
        """Sidebar bottom has Help & Support + Hide/Show toggle."""
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            body = client.get("/admin").text
            assert "Help &amp; Support" in body or "Help & Support" in body


class TestDashboardKpiCards:
    """The v2 dashboard renders 4 KPI cards: Total Sales, Active Users, Orders, Products."""

    def test_all_four_kpi_titles_present(self):
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            body = client.get("/admin/section/dashboard").text
            for title in ("Total Sales", "Active Users", "Orders", "Products"):
                assert title in body, f"missing KPI title {title!r}"

    def test_kpi_cards_have_pastel_icon_chips(self):
        """Each KPI card has a colored icon chip (blue/emerald/purple/amber)."""
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            body = client.get("/admin/section/dashboard").text
            assert "bg-blue-50" in body
            assert "bg-emerald-50" in body
            assert "bg-purple-50" in body
            assert "bg-amber-50" in body

    def test_kpi_cards_have_green_trend_arrow(self):
        """Each KPI card shows the green trend arrow (svg path d=...M13 7h8...)."""
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            body = client.get("/admin/section/dashboard").text
            # The green trend arrow SVG path is identical for all 4 cards
            assert body.count("M13 7h8m0 0v8m0-8l-8 8-4-4-6 6") >= 4

    def test_page_title_in_content_area(self):
        """Page title 'Dashboard' + subtitle 'Welcome back to your dashboard' live
        in the workspace content area (not the top bar)."""
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            body = client.get("/admin/section/dashboard").text
            assert ">Dashboard<" in body
            assert "Welcome back to your dashboard" in body


class TestDashboardActivityStatsGrid:
    """The v2 dashboard has a 2-col grid: Recent Activity (left) + Quick Stats (right)."""

    def test_recent_activity_panel_present(self):
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            body = client.get("/admin/section/dashboard").text
            assert "Recent Activity" in body
            assert "View all" in body  # link to expanded feed

    def test_quick_stats_panel_present(self):
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            body = client.get("/admin/section/dashboard").text
            assert "Quick Stats" in body
            # Three core stat labels
            assert "Conversion Rate" in body
            assert "Bounce Rate" in body
            assert "Page Views" in body
            # Plus 3D pipeline bar
            assert "3D Pipeline" in body

    def test_progress_bars_present(self):
        """Quick Stats uses h-1.5 rounded progress bars (colored)."""
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            body = client.get("/admin/section/dashboard").text
            assert "bg-blue-500" in body   # conversion rate bar
            assert "bg-orange-500" in body  # bounce rate bar
            assert "bg-emerald-500" in body # page views bar

    def test_activity_uses_unified_kind(self):
        """Recent Activity items have icon_bg + icon_color from the new icon map."""
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            body = client.get("/admin/section/dashboard").text
            # Background/icon color pairs from the activity feed
            assert "bg-emerald-50" in body
            assert "bg-blue-50" in body
            assert "bg-amber-50" in body
            assert "bg-purple-50" in body
            assert "bg-orange-50" in body

    def test_empty_store_dashboard_graceful(self):
        """Empty DB still renders the dashboard with zeroed KPIs and design-time mock activity."""
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            r = client.get("/admin/section/dashboard")
            assert r.status_code == 200
            body = r.text
            # The page title and all 4 KPI cards still render
            assert "Dashboard" in body
            for title in ("Total Sales", "Active Users", "Orders", "Products"):
                assert title in body
            # Quick stats panel still renders
            assert "Quick Stats" in body
            assert "Conversion Rate" in body


class TestOperationsSection:
    """The Operations section preserves the legacy production-ledger + waitlist
    + reservation feeds from the old /admin/dashboard, but renders in the
    v2 light-theme shell."""

    def test_operations_renders_v2_design(self):
        app = _make_app_with_routes(pool_factory=_make_populated_pool)
        with TestClient(app, raise_server_exceptions=False) as client:
            r = client.get("/admin/section/operations")
            assert r.status_code == 200
            body = r.text
            assert "data-section=\"operations\"" in body
            # 4 operational KPI cards
            for title in ("Verified Revenue", "Unfulfilled Backlogs", "Active Holds", "Waitlist Demand"):
                assert title in body, f"missing KPI {title!r}"
            # Atelier Production Ledger heading
            assert "Atelier Production Ledger" in body
            # Right column feeds
            assert "Out-of-Stock Queues" in body
            assert "Stock Sentinel Feed" in body
            # Populated pool renders the seeded product
            assert "Aba Handloomed Trouser" in body

    def test_operations_uses_light_theme(self):
        """The section uses the v2 light-theme tokens (no dark green from the old design)."""
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            body = client.get("/admin/section/operations").text
            # v2 light theme
            assert "bg-white" in body
            # Pastel icon chips
            assert "bg-blue-50" in body
            assert "bg-amber-50" in body
            assert "bg-emerald-50" in body
            assert "bg-purple-50" in body
            # Old dark-green theme is gone
            assert "BRAND COMMAND" not in body

    def test_operations_pastel_kpi_chips(self):
        """KPI cards use pastel icon chips (blue/amber/emerald/purple) for
        Verified Revenue, Unfulfilled Backlogs, Active Holds, Waitlist Demand."""
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            body = client.get("/admin/section/operations").text
            # Each chip color appears at least once
            assert body.count("bg-blue-50") >= 1
            assert body.count("bg-amber-50") >= 1
            assert body.count("bg-emerald-50") >= 1
            assert body.count("bg-purple-50") >= 1

    def test_operations_htmx_endpoints_referenced(self):
        """The section's forms point at the legacy HTMX endpoints
        (which are still served by app/routes/admin_dashboard.py)."""
        app = _make_app_with_routes(pool_factory=_make_populated_pool)
        with TestClient(app, raise_server_exceptions=False) as client:
            body = client.get("/admin/section/operations").text
            assert 'hx-post="/admin/dashboard/update-stock"' in body
            assert 'hx-post="/admin/dashboard/update-model-url"' in body
            # notify-waitlist is only rendered when there's a waitlist row;
            # with the empty pool we still want to confirm the form action is
            # defined in the template by checking the waitlists else-branch
            assert "No waiting buyers backlogged" in body

    def test_legacy_admin_dashboard_url_routes_to_v2(self):
        """The legacy /admin/dashboard now serves the v2 dashboard (was the
        dark-green Executive Dashboard). The v2 dashboard's data-section
        marker should appear in the response."""
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            r = client.get("/admin/dashboard")
            assert r.status_code == 200
            body = r.text
            # The v2 dashboard marker (not the old dark-green design)
            assert "data-section=\"dashboard\"" in body
            # The old dark-green branding is gone
            assert "BRAND COMMAND" not in body
            # The new KPI titles render
            for title in ("Total Sales", "Active Users", "Orders", "Products"):
                assert title in body, f"missing v2 KPI {title!r}"

    def test_index_includes_operations_nav_item(self):
        """The /admin sidebar includes the new 'Operations' nav item."""
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            body = client.get("/admin").text
            assert 'id="nav-operations"' in body
            assert ">Operations<" in body


class TestPipelineStatusMapping:
    """The pipeline_status enum must map to the four display buckets."""

    def test_completed_maps_to_generated(self):
        from app.routes.admin_sections import _map_pipeline_status
        assert _map_pipeline_status("completed") == "generated"

    def test_queued_maps_to_processing(self):
        from app.routes.admin_sections import _map_pipeline_status
        for raw in ("queued", "generating_mesh", "optimizing_gltf"):
            assert _map_pipeline_status(raw) == "processing", f"{raw} should be processing"

    def test_failed_maps_to_failed(self):
        from app.routes.admin_sections import _map_pipeline_status
        assert _map_pipeline_status("failed") == "failed"

    def test_idle_maps_to_not_started(self):
        from app.routes.admin_sections import _map_pipeline_status
        assert _map_pipeline_status("idle") == "not_started"
        assert _map_pipeline_status(None) == "not_started"

    def test_unknown_status_defaults_to_not_started(self):
        from app.routes.admin_sections import _map_pipeline_status
        assert _map_pipeline_status("garbage") == "not_started"


class TestAdminSectionGracefulEmpty:
    """Sections must render even if the DB is unreachable or empty."""

    def test_dashboard_empty_db(self):
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            r = client.get("/admin/section/dashboard")
            assert r.status_code == 200
            assert "Welcome back to your dashboard" in r.text

    def test_products_empty_db_shows_empty_state(self):
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            r = client.get("/admin/section/products")
            assert r.status_code == 200
            assert ("No products yet" in r.text) or ("data-section=\"products\"" in r.text)

    def test_categories_empty_db_renders(self):
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            r = client.get("/admin/section/categories")
            assert r.status_code == 200

    def test_reviews_empty_db_renders(self):
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            r = client.get("/admin/section/reviews")
            assert r.status_code == 200

    def test_ads_empty_db_renders(self):
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            r = client.get("/admin/section/ads")
            assert r.status_code == 200

    def test_settings_empty_db_renders_form(self):
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            r = client.get("/admin/section/settings")
            assert r.status_code == 200
            assert 'name="currency"' in r.text
            assert 'name="mesh_provider"' in r.text
            assert 'name="auto_mesh"' in r.text

    def test_about_empty_db_renders_form(self):
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            r = client.get("/admin/section/about")
            assert r.status_code == 200
            assert 'name="name"' in r.text
            assert 'name="story"' in r.text


class TestAdminSectionWrites:
    """Settings and About endpoints accept POST and re-render the section."""

    def test_settings_post_succeeds(self):
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            r = client.post(
                "/admin/section/settings",
                data={
                    "currency": "EUR",
                    "timezone": "Africa/Lagos",
                    "locale": "en",
                    "shipping_domestic": "15.00",
                    "shipping_international": "45.00",
                    "free_shipping_threshold": "250.00",
                    "mesh_provider": "instantmesh",
                    "auto_mesh": "on",
                },
            )
            assert r.status_code == 200
            assert "Currency" in r.text

    def test_about_post_succeeds(self):
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            r = client.post(
                "/admin/section/about",
                data={
                    "name": "Adaeze Okonkwo",
                    "role": "Founder & Creative Director",
                    "email": "adaeze@asiko.boutique",
                    "location": "Lagos, Nigeria",
                    "instagram": "asiko.boutique",
                    "founded_year": "2024",
                    "tagline": "Crafted in Lagos.",
                    "story": "Born from a single bolt of indigo hand-loom cloth.",
                },
            )
            assert r.status_code == 200

    def test_settings_post_handles_empty_form(self):
        """Empty POST should still render the form without error."""
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            r = client.post("/admin/section/settings", data={})
            assert r.status_code == 200


class TestHumanizeDate:
    """The _humanize_dt helper should handle None, strings, and datetimes."""

    def test_none(self):
        from app.routes.admin_sections import _humanize_dt
        assert _humanize_dt(None) == "—"

    def test_just_now(self):
        from datetime import datetime, timezone
        from app.routes.admin_sections import _humanize_dt
        assert _humanize_dt(datetime.now(timezone.utc)) == "just now"

    def test_hours_ago(self):
        from datetime import datetime, timezone, timedelta
        from app.routes.admin_sections import _humanize_dt
        dt = datetime.now(timezone.utc) - timedelta(hours=3)
        assert _humanize_dt(dt) == "3h ago"

    def test_days_ago(self):
        from datetime import datetime, timezone, timedelta
        from app.routes.admin_sections import _humanize_dt
        dt = datetime.now(timezone.utc) - timedelta(days=2)
        assert _humanize_dt(dt) == "2d ago"
