# ASIKO Boutique — Virtual Experience Session Routes
# Session-bound avatar selection endpoint.
# Persists preferred_avatar_axis to encrypted session context.

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route


async def update_session_avatar_profile(request: Request) -> JSONResponse:
    """Saves the user's current avatar preference to avoid interface resets during navigation."""
    payload = await request.json()
    selected_gender = payload.get("gender", "female")

    if selected_gender not in ["male", "female"]:
        return JSONResponse(
            {"status": "error", "message": "INVALID_GENDER_AXIS"},
            status_code=400,
        )

    request.session["preferred_avatar_axis"] = selected_gender
    return JSONResponse({"status": "success", "avatar_profile": selected_gender})


routes = [
    Route(
        "/api/virtual/avatar-profile",
        endpoint=update_session_avatar_profile,
        methods=["POST"],
    ),
]
