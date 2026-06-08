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
    ("/admin/section/sales",         "data-section=\"sales\""),
    ("/admin/section/view-site",     "data-section=\"view-site\""),
    ("/admin/section/products",      "data-section=\"products\""),
    ("/admin/section/categories",    "data-section=\"categories\""),
    ("/admin/section/analytics",     "data-section=\"analytics\""),
    ("/admin/section/members",       "data-section=\"members\""),
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


class TestDirectNavigationShell:
    """Direct browser navigation to section URLs returns the full admin shell."""

    def test_direct_nav_returns_admin_shell(self):
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            r = client.get("/admin/section/members")
            assert r.status_code == 200
            # Should contain the admin shell markers
            assert "ÀSÌKÒ" in r.text
            assert "nav-members" in r.text
            # Should also contain the section content
            assert 'data-section="members"' in r.text

    def test_htmx_nav_returns_raw_fragment(self):
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            r = client.get("/admin/section/members", headers={"HX-Request": "true"})
            assert r.status_code == 200
            # Should NOT contain the admin shell markers
            assert "ÀSÌKÒ" not in r.text
            assert "nav-members" not in r.text
            # Should still contain the section content
            assert 'data-section="members"' in r.text

    def test_direct_nav_dashboard_returns_shell(self):
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            r = client.get("/admin/section/dashboard")
            assert r.status_code == 200
            assert "ÀSÌKÒ" in r.text
            assert 'data-section="dashboard"' in r.text


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
            # 10 nav items, each with id="nav-XXX"
            for nav_id in (
                "nav-dashboard", "nav-sales", "nav-view-site",
                "nav-products", "nav-categories", "nav-analytics",
                "nav-members", "nav-operations", "nav-settings", "nav-about",
            ):
                assert nav_id in body, f"missing nav id {nav_id}"

    def test_index_uses_htmx_workspace_target(self):
        """The workspace hx-target is #workspace-content (NOT #workspace).

        Regression: <main id="workspace" hx-trigger="load"> must target the inner
        #workspace-content div, otherwise the initial dashboard swap replaces
        the entire <main> element (including the top bar and the swap target),
        which breaks every subsequent nav click.
        """
        import re
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            r = client.get("/admin")
            body = r.text
            # The <main id="workspace"> block must contain hx-target="#workspace-content"
            # within its opening tag (i.e. on the same element as hx-trigger="load").
            main_match = re.search(
                r'<main\b[^>]*id="workspace"[^>]*>',
                body,
                re.DOTALL,
            )
            assert main_match, "<main id=\"workspace\"> not found in /admin response"
            main_tag = main_match.group(0)
            assert 'hx-trigger="load"' in main_tag
            assert 'hx-target="#workspace-content"' in main_tag, (
                "hx-trigger=load on <main> must target #workspace-content; "
                "otherwise the initial load swaps the whole <main> element and "
                "breaks every subsequent nav click."
            )
            # The #workspace-content div must exist in the response (the swap target).
            assert 'id="workspace-content"' in body

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

    def test_dark_mode_toggle_present(self):
        """Admin top bar has a dark mode toggle button with sun/moon SVG."""
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            body = client.get("/admin").text
            assert "title=\"Toggle theme\"" in body
            # Has a toggle button that modifies localStorage
            assert "asiko:darkMode" in body

    def test_dark_mode_fouc_prevention_script(self):
        """Admin shell has a synchronous script to prevent flash of unstyled content."""
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            body = client.get("/admin").text
            assert "asiko:darkMode" in body
            # The sync script should be in <head>, not inside a deferred Alpine
            assert '<script>\n        // Apply persisted theme synchronously' in body

    def test_dark_mode_dark_class_configured(self):
        """Admin shell uses Tailwind darkMode: 'class' and Alpine dark state."""
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            body = client.get("/admin").text
            assert "darkMode: 'class'" in body
            assert "'dark': darkMode" in body


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
            # 4 operational KPI cards (plain language)
            for title in ("Total Sales", "Pending Orders", "Reserved Items", "Waiting Customers"):
                assert title in body, f"missing KPI {title!r}"
            # Stock Management heading
            assert "Stock Management" in body
            # Photo to 3D section
            assert "Photo to 3D" in body
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
            # notify-waitlist is only rendered when there's a waitlist row;
            # with the empty pool we still want to confirm the waitlist
            # section renders with the empty-state message
            assert "Nobody waiting" in body or "No waiting" in body

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


class TestNewSections:
    """The 4 distinct sections added to fill gaps in the v2 sidebar:
    Sales (orders), Analytics (traffic), Members (customers), View Site (preview).
    """

    # ---------------- Sales ----------------
    def test_sales_section_renders(self):
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            r = client.get("/admin/section/sales")
            assert r.status_code == 200
            body = r.text
            assert "data-section=\"sales\"" in body
            # 4 KPI titles
            for title in ("Gross Revenue", "Paid Orders", "Pending", "Fulfilled"):
                assert title in body, f"missing KPI {title!r}"
            # Empty state copy
            assert "No orders yet" in body
            # Status filter chips
            for status in ("Paid", "Pending", "Shipped", "Delivered", "Cancelled", "Processing"):
                assert status in body, f"missing status chip {status!r}"

    def test_sales_section_uses_v2_light_theme(self):
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            body = client.get("/admin/section/sales").text
            assert "bg-emerald-50" in body
            assert "bg-blue-50" in body
            assert "bg-amber-50" in body
            assert "bg-purple-50" in body
            assert "BRAND COMMAND" not in body  # v2 only

    def test_sales_section_renders_with_real_uuid_order_id(self):
        """Regression: order.id from asyncpg is a pgproto.UUID (not subscriptable).
        The sales template does `o.id[:8]`, so the route must coerce it to a
        plain string before passing to the template."""
        import uuid as uuidlib
        order_id = uuidlib.UUID("abcd1234-5678-90ab-cdef-1234567890ab")

        def _make_uuid_pool():
            pool = MagicMock()
            order_row = {
                "id": order_id,
                "customer_email": "jane.doe@asiko.com",
                "total_amount": 25000.0,
                "shipping_state": "Lagos",
                "shipping_cost": 1500.0,
                "status": "paid",
                "payment_reference": "PAY-001",
                "created_at": None,
                "item_count": 2,
            }

            @asynccontextmanager
            async def _acquire():
                conn = MagicMock()
                conn.fetch = AsyncMock(return_value=[order_row])
                conn.fetchrow = AsyncMock(return_value=None)
                conn.fetchval = AsyncMock(return_value=0)
                conn.execute = AsyncMock(return_value=None)
                yield conn

            pool.acquire = _acquire
            return pool

        app = _make_app_with_routes(pool_factory=_make_uuid_pool)
        with TestClient(app, raise_server_exceptions=False) as client:
            r = client.get("/admin/section/sales")
            assert r.status_code == 200, f"got {r.status_code}: {r.text[:400]}"
            body = r.text
            # Order id should be rendered as a string, with the 8-char prefix
            # ("#abcd1234") visible in the table. Without str() coercion in
            # the route, the slice would TypeError and the response would be 500.
            assert "#abcd1234" in body
            # Customer email should also render (proves we didn't crash mid-row).
            assert "jane.doe@asiko.com" in body

    def test_sales_sidebar_nav_active_for_slug_sales(self):
        """The idMap must map slug 'sales' to nav button 'nav-sales'."""
        import re
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            body = client.get("/admin").text
            assert re.search(r"'sales'\s*:\s*'nav-sales'", body)
            assert "id=\"nav-sales\"" in body

    # ---------------- Analytics ----------------
    def test_analytics_section_renders(self):
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            r = client.get("/admin/section/analytics")
            assert r.status_code == 200
            body = r.text
            assert "data-section=\"analytics\"" in body
            for title in ("Sessions", "Page Views", "Conversion Rate", "Avg. Session"):
                assert title in body, f"missing KPI {title!r}"
            # 7-day revenue + funnel + sources
            assert "7-day revenue" in body
            assert "Conversion funnel" in body
            assert "Traffic sources" in body
            # Funnel steps
            for step in ("Visitors", "Product views", "Add to cart", "Checkout", "Purchased"):
                assert step in body, f"missing funnel step {step!r}"

    def test_analytics_handles_no_orders(self):
        """Empty DB should still render the chart + funnel with mock data."""
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            body = client.get("/admin/section/analytics").text
            # 7-day series renders even with zero paid orders
            for day in ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"):
                assert day in body
            assert "12,480" in body or "12480" in body  # sessions KPI
            # Sources
            for src in ("Direct", "Instagram", "Google search", "Email"):
                assert src in body

    def test_analytics_sidebar_nav(self):
        import re
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            body = client.get("/admin").text
            assert re.search(r"'analytics'\s*:\s*'nav-analytics'", body)
            assert "id=\"nav-analytics\"" in body

    # ---------------- Members ----------------
    def test_members_section_renders(self):
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            r = client.get("/admin/section/members")
            assert r.status_code == 200
            body = r.text
            assert "data-section=\"members\"" in body
            for title in ("Total Members", "Active", "New", "Lifetime Value"):
                assert title in body, f"missing KPI {title!r}"
            # Status chips
            for status in ("Active", "New", "Returning"):
                assert status in body, f"missing status {status!r}"
            # Empty state
            assert "No members yet" in body

    def test_members_section_pastel_chips(self):
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            body = client.get("/admin/section/members").text
            assert "bg-blue-50" in body
            assert "bg-emerald-50" in body
            assert "bg-purple-50" in body
            assert "bg-amber-50" in body

    def test_members_sidebar_nav(self):
        import re
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            body = client.get("/admin").text
            assert re.search(r"'members'\s*:\s*'nav-members'", body)
            assert "id=\"nav-members\"" in body

    # ---------------- View Site ----------------
    def test_view_site_section_renders(self):
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            r = client.get("/admin/section/view-site")
            assert r.status_code == 200
            body = r.text
            assert "data-section=\"view-site\"" in body
            # Live preview iframe
            assert "<iframe" in body
            assert 'title="Storefront preview"' in body
            # 4 status counts
            for label in ("Products live", "Categories", "Stores", "Orders"):
                assert label in body, f"missing count label {label!r}"
            # Open in new tab CTA
            assert "Open in new tab" in body

    def test_view_site_sidebar_nav(self):
        import re
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            body = client.get("/admin").text
            assert re.search(r"'view-site'\s*:\s*'nav-view-site'", body)
            assert "id=\"nav-view-site\"" in body
            # The view-site button uses hx-get (not an external <a>) so it
            # is part of the in-shell section rotation
            assert 'hx-get="/admin/section/view-site"' in body

    # ---------------- All 4 are in PAGE_META + idMap ----------------
    def test_all_new_sections_in_page_meta_and_idmap(self):
        import re
        app = _make_app_with_routes()
        with TestClient(app, raise_server_exceptions=False) as client:
            body = client.get("/admin").text
            for nav_id in ("nav-sales", "nav-view-site", "nav-analytics", "nav-members"):
                assert nav_id in body, f"missing PAGE_META key {nav_id}"
            # The idMap is rendered as a JS object literal — keys may be aligned
            # with extra whitespace. Use regex to be tolerant of that.
            for slug, nav_id in (
                ("sales",      "nav-sales"),
                ("view-site",  "nav-view-site"),
                ("analytics",  "nav-analytics"),
                ("members",    "nav-members"),
            ):
                pattern = rf"'{slug}'\s*:\s*'{nav_id}'"
                assert re.search(pattern, body), f"missing idMap entry for {slug}"


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
