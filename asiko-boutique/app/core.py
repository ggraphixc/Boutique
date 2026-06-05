# ASIKO Boutique - Shared Core Module
# Single source of truth for template loading, filters, and session helpers.
# Avoids circular imports between main.py and route files.

from starlette.templating import Jinja2Templates
from starlette.requests import Request

# Initialize Jinja2 with custom environment configurations
templates = Jinja2Templates(directory="app/templates")


# Custom filter to format currency cleanly without external dependencies
def naira_format(value: float | int) -> str:
    try:
        return f"₦{int(value):,}"
    except (ValueError, TypeError):
        return f"₦{value}"


# Register the filter directly into the Jinja2 engine environment
templates.env.filters["naira"] = naira_format


def get_cart_from_session(request: Request) -> dict:
    """Retrieve the active cart dictionary using the clean 'lines' key specification."""
    return request.session.get("cart", {"lines": [], "total": 0.0, "item_count": 0})


def save_cart_to_session(request: Request, cart: dict) -> None:
    """Persist the active cart back to the encrypted client cookie session."""
    request.session["cart"] = cart
