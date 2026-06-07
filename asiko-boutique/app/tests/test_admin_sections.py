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


def _make_app_with_routes():
    """Fresh Starlette app with just the admin section routes + mocked pool.
    SessionMiddleware is required because base.html reads request.session."""
    test_app = Starlette(
        routes=admin_sections_routes,
        middleware=[Middleware(SessionMiddleware, secret_key="test-key", session_cookie="asiko_test")],
    )
    test_app.state.db_pool = _make_empty_pool()
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
            # 8 nav items, each with id="nav-XXX"
            for nav_id in (
                "nav-dashboard", "nav-products", "nav-categories", "nav-all-products",
                "nav-reviews", "nav-ads", "nav-settings", "nav-about",
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
            assert "Atelier overview" in r.text

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
