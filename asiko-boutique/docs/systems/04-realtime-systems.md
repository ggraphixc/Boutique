# D. REAL-TIME SYSTEMS

## Overview

ASIKO Boutique uses 4 real-time systems to push live updates to admin and storefront without page reloads. Built on Postgres LISTEN/NOTIFY → WebSocket broadcast and Server-Sent Events.

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
        # Prune dead connections
        for ws in dead:
            self.connections[channel].remove(ws)
```

### Postgres LISTEN/NOTIFY
```python
async def _listen(self, pool, channel):
    """Background task: listens for Postgres NOTIFY on a channel."""
    while True:
        try:
            async with pool.acquire() as conn:
                await conn.add_listener(channel, self._on_notify)
                # Keep listening...
        except Exception:
            await asyncio.sleep(5)  # Reconnect on failure

def _on_notify(self, connection, pid, channel, payload):
    """Called when a NOTIFY is received."""
    data = json.loads(payload)
    asyncio.create_task(self.broadcast(channel, data))
```

### Helper Function
```python
async def notify(pool, channel, data):
    """Send a NOTIFY to a Postgres channel."""
    async with pool.acquire() as conn:
        await conn.execute(
            "SELECT pg_notify($1, $2)",
            channel, json.dumps(data)
        )
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

#### Dashboard WebSocket
```python
async def ws_admin_dashboard(websocket):
    """
    WS /ws/admin/dashboard
    Subscribes to: new_order, new_review
    Pushes: KPI cards, activity feed items
    """
    await manager.connect(websocket, "new_order")
    await manager.connect(websocket, "new_review")
    try:
        while True:
            await websocket.receive_text()  # Keep alive
    except WebSocketDisconnect:
        manager.disconnect(websocket, "new_order")
        manager.disconnect(websocket, "new_review")
```

**Pushed Fragments:**

When `new_order` fires:
```html
<!-- _rt_kpi_cards.html -->
<div id="kpi-cards" hx-swap="innerHTML">
  <div class="kpi-card">
    <span class="kpi-value">{{ total_sales|naira }}</span>
    <span class="kpi-label">Total Sales</span>
  </div>
  <!-- ... more KPI cards -->
</div>
```

When `new_review` fires:
```html
<!-- _rt_activity_feed.html -->
<div id="activity-feed" hx-swap="afterbegin">
  <div class="activity-item">
    <span class="text-amber-500">★</span>
    {{ customer_name }} reviewed {{ product_name }}
  </div>
</div>
```

#### Reviews WebSocket
```python
async def ws_admin_reviews(websocket):
    """
    WS /ws/admin/reviews
    Subscribes to: new_review
    Pushes: Updated review summary stats
    """
```

**Pushed Fragment:**
```html
<!-- _rt_review_stats.html -->
<div id="review-stats">
  <span>Average: {{ avg_rating }}</span>
  <span>Total: {{ total_reviews }}</span>
</div>
```

### Why It Matters
Admin sees live updates without refreshing. New orders appear instantly. Reviews show up in real-time.

---

## 3. Store WebSocket Endpoints

**File:** `app/routes/ws_store.py`

### What It Does
Public-facing WebSocket endpoints for real-time product detail page updates. Shows live stock levels and review counts.

### Endpoint

#### Product WebSocket
```python
async def ws_store_product(websocket):
    """
    WS /ws/store/product/{product_id}
    Subscribes to: new_review (for this product), stock_update (for this product)
    Pushes: Review stats, stock badge
    """
    product_id = websocket.path_params["product_id"]
    await manager.connect(websocket, "new_review")
    await manager.connect(websocket, "stock_update")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, "new_review")
        manager.disconnect(websocket, "stock_update")
```

**Pushed Fragments:**

Review stats:
```html
<div id="review-summary">
  <span class="text-amber-500">★★★★★</span>
  <span>{{ avg_rating }} ({{ count }} reviews)</span>
</div>
```

Stock badge:
```html
<div id="stock-badge" class="...">
  {% if stock > 0 %}
    <span class="text-emerald-600">In Stock</span>
  {% else %}
    <span class="text-red-600">Out of Stock</span>
  {% endif %}
</div>
```

### Why It Matters
Customers see stock changes without refreshing. If someone else buys the last item, the stock badge updates live.

---

## 4. SSE Pipeline Stream

**File:** `app/routes/sse_streams.py`

### What It Does
Server-Sent Events endpoint for streaming 3D pipeline status updates. Persistent HTTP connection that pushes status transitions.

### Endpoint

```python
async def stream_pipeline_status(request):
    """
    GET /api/stream/pipeline/{product_id}
    SSE: Persistent HTTP connection
    Polls: products.pipeline_status every 2 seconds
    Pushes: Status transitions (in_progress → completed/failed)
    """
```

### SSE Format
```
data: {"status": "in_progress", "product_id": "uuid"}

data: {"status": "completed", "product_id": "uuid", "model_3d_url": "/static/uploads/optimized/mesh.glb"}

data: {"status": "failed", "product_id": "uuid", "error": "Generation timeout"}
```

### Flow
```
1. Client opens SSE connection: GET /api/stream/pipeline/{product_id}
2. Server keeps connection open
3. Every 2 seconds, server queries: SELECT pipeline_status FROM products WHERE id = $1
4. If status changed since last check:
   a. Send SSE event with new status
   b. If terminal state (completed/failed), close connection
5. Client receives events and updates UI
```

### Why It Matters
3D model generation takes 30-60 seconds. SSE shows progress without polling.

---

## Summary

| System | File | Lines | Key Feature |
|--------|------|-------|-------------|
| Connection Manager | `app/realtime.py` | ~100 | Postgres LISTEN/NOTIFY → WebSocket |
| Admin WebSocket | `app/routes/ws_admin.py` | ~150 | Live KPIs, activity feed, review stats |
| Store WebSocket | `app/routes/ws_store.py` | ~80 | Live stock badge, review counts |
| SSE Pipeline | `app/routes/sse_streams.py` | ~60 | 3D pipeline status streaming |

**Total: ~390 lines of code**
