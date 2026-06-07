# ASIKO Boutique - Digital Product Passport Verification Routes
# Avatar profile binding endpoint for gender-based skeleton fit selection

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route


VALID_GENDERS = {"male", "female", "unisex"}


async def set_avatar_profile(request: Request) -> JSONResponse:
    """POST /api/virtual/profile/set - Bind avatar gender profile to session."""
    try:
        data = await request.json()
    except Exception:
        return JSONResponse(
            {"error": "Invalid JSON payload"},
            status_code=400,
        )

    # Defensive read: missing key defaults to "female", but the .get() default
    # does NOT protect against {"gender": ""} or whitespace-only strings. We
    # normalize + guard here so an empty value can never reach the validator
    # (which would 400 unnecessarily) or be persisted to the session.
    raw_gender = data.get("gender") if isinstance(data, dict) else None
    gender = (raw_gender or "female").strip() or "female"

    if gender not in VALID_GENDERS:
        return JSONResponse(
            {"error": "Invalid gender value. Must be one of: male, female, unisex"},
            status_code=400,
        )

    request.session["preferred_avatar_axis"] = gender

    return JSONResponse(
        {"avatar_profile": gender, "status": "bound"},
    )


routes = [
    Route("/api/virtual/profile/set", endpoint=set_avatar_profile, methods=["POST"]),
]