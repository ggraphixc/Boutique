# D. REAL-TIME SYSTEMS

## Overview

ASIKO Boutique uses 3 real-time systems to push live updates to admin and storefront without page reloads. Built on Postgres LISTEN/NOTIFY → WebSocket broadcast and HTMX on-demand polling.

---

## 1. WebSocket Connection Manager

**File:** `app/realtime.py`

### What It Does
Centralized pub/sub hub that converts Postgres database events into WebSocket broadcasts. No Redis required — uses Postgres's built-in LISTEN/NOTIFY.

### Architecture
```
Postgres NOTIFY → LISTEN handler → ConnectionManager → WebSocket broadcast
```

### ConnectionManager Class
```python
class ConnectionManager:
    def __init__(self):
        self.connections: dict[str, list[WebSocket]] = {}
        self.listeners: list[asyncio.Task] = []

    async def connect(self, websocket, channel):
        """Register a WebSocket connection to a channel."""
        await websocket.accept()
        if channel not in self.connections:
            self.connections[channel] = []
        self.connections[channel].append(websocket)

    def disconnect(self, websocket, channel):
        """Remove a WebSocket from a channel."""
        if channel in self.connections:
            self.connections[channel] = [
                ws for ws in self.connections[channel] if ws != websocket
            ]

    async def broadcast(self, channel, data):
        """Send data to all connected WebSockets on a channel."""
        if channel not in self.connections:
            return
        dead = []
        for ws in self.connections[channel]:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.connections[channel].remove(ws)
```

### 3 Real-Time Channels

| Channel | Event | Payload |
|---------|-------|---------|
| `new_review` | Customer submits review | `{product_id, rating, customer_name}` |
| `new_order` | Order placed | `{order_id, total, customer_email}` |
| `stock_update` | Stock changes | `{variant_id, new_stock, product_id}` |

### Why It Matters
Without Redis, this is the cheapest way to get real-time updates. Postgres does the heavy lifting.

---

## 2. Admin WebSocket Endpoints

**File:** `app/routes/ws_admin.py`

### What It Does
Provides real-time HTMX WebSocket endpoints for the admin dashboard. Pushes live KPI updates, activity feed items, and review statistics.

### Endpoints

#### Dashboard WebSocket (`WS /ws/admin/dashboard`)
- Subscribes to: `new_order`, `new_review`
- Pushes: KPI cards, activity feed items

#### Reviews WebSocket (`WS /ws/admin/reviews`)
- Subscribes to: `new_review`
- Pushes: Updated review summary stats

### Why It Matters
Admin sees live updates without refreshing. New orders appear instantly. Reviews show up in real-time.

---

## 3. Store WebSocket Endpoints

**File:** `app/routes/ws_store.py`

### What It Does
Public-facing WebSocket endpoints for real-time product detail page updates. Shows live stock levels and review counts.

### Endpoint

#### Product WebSocket (`WS /ws/store/product/{product_id}`)
- Subscribes to: `new_review` (for this product), `stock_update` (for this product)
- Pushes: Review stats, stock badge

### Why It Matters
Customers see stock changes without refreshing. If someone else buys the last item, the stock badge updates live.

---

## 4. Notification Bell (HTMX On-Demand)

**Route:** `GET /admin/rt/notifications`
**Handler:** `rt_notifications()` in `app/routes/admin_sections.py`
**Template:** `app/templates/admin/sections/_rt_notifications.html`

### What It Does
Fetches fresh notification data when the admin clicks the bell icon. Returns an HTML fragment for the dropdown and an `X-Unread-Count` header for the dynamic badge.

### Activity Types (7)

| Type | Source Table | Time Window | Icon | Color |
|------|-------------|-------------|------|-------|
| Order | `orders` | 24h | Shopping bag | Emerald |
| Customer | `customers` | 24h | Person | Blue |
| Review | `product_reviews` | 7 days | Star | Amber |
| Low stock | `products` (≤5 qty) | All | Alert triangle | Rose |
| Waitlist | `waitlist` | 24h | Clock | Purple |
| Email | `email_logs` | 24h | Envelope | Teal |
| Contact | `contact_messages` | 24h | Chat bubble | Indigo |

### Settings Awareness
Respects `notification_settings` toggles:
- `notif_new_order` — show/hide order notifications
- `notif_review` — show/hide review notifications
- `notif_low_stock` — show/hide low stock alerts

### Response
- HTML fragment swapped into `#notifications-dropdown`
- `X-Unread-Count` header for Alpine.js badge update
- Notifications sorted by timestamp (newest first), capped at 15
- All queries wrapped in `try/except` for graceful degradation

### Frontend Wiring
- Alpine.js `x-data` on bell container manages `open` and `unread` state
- `loadNotifs()` function uses `fetch()` API, reads `X-Unread-Count` header
- "Mark all as read" button resets unread to 0
- Responsive dropdown: `w-72` mobile, `w-[340px]` desktop
- Loading spinner on initial load

---

## Summary

| System | File | Key Feature |
|--------|------|-------------|
| Connection Manager | `app/realtime.py` | Postgres LISTEN/NOTIFY → WebSocket |
| Admin WebSocket | `app/routes/ws_admin.py` | Live KPIs, activity feed, review stats |
| Store WebSocket | `app/routes/ws_store.py` | Live stock badge, review counts |
| Notification Bell | `admin_sections.py` + `_rt_notifications.html` | 7 activity types, dynamic unread badge |
