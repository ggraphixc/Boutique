# ASIKO Boutique - Async PostgreSQL Database Pool Lifecycle
# Pool allocation via os.getenv, returned directly for lifespan binding.

import os
import sys
import logging
from typing import Optional, Any

import asyncpg

logger = logging.getLogger("asiko.database")
_pool: Optional[asyncpg.Pool] = None


async def init_db_pool() -> asyncpg.Pool:
    """
    Reads DATABASE_URL from environment and allocates a production-grade
    asyncpg connection pool. Returns the pool for app.state binding.
    """
    global _pool

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("[DATABASE ERROR] CRITICAL: DATABASE_URL variable is missing from environment.")
        sys.exit(1)

    import asyncio
    for attempt in range(4):
        try:
            _pool = await asyncpg.create_pool(
                dsn=database_url,
                min_size=2,
                max_size=10,
                command_timeout=60.0,
                max_inactive_connection_lifetime=300.0,
            )
            print("[DATABASE] Connection pool allocated via asyncpg.")
            return _pool
        except Exception as e:
            wait = 2 ** attempt * 2
            print(f"[DATABASE] Attempt {attempt+1}/4 failed: {e}")
            if attempt < 3:
                print(f"[DATABASE] Retrying in {wait}s...")
                await asyncio.sleep(wait)
    print("[DATABASE ERROR] CRITICAL: Could not connect after 4 attempts.")
    sys.exit(1)


async def close_db_pool() -> None:
    """Gracefully terminates all active connections within the pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        print("[DATABASE] Connection pool terminated.")
        _pool = None


def get_db_pool() -> asyncpg.Pool:
    """Retrieves the active connection pool instance."""
    if _pool is None:
        raise RuntimeError("Database connection pool is not initialized.")
    return _pool


# ---------------------------------------------------------------------------
# Generic Query Executors
# ---------------------------------------------------------------------------

async def fetch_all(query: str, *args: Any) -> list[asyncpg.Record]:
    pool = get_db_pool()
    async with pool.acquire() as conn:
        return await conn.fetch(query, *args)


async def fetch_one(query: str, *args: Any) -> Optional[asyncpg.Record]:
    pool = get_db_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow(query, *args)


async def execute(query: str, *args: Any) -> str:
    pool = get_db_pool()
    async with pool.acquire() as conn:
        return await conn.execute(query, *args)


async def execute_returning(query: str, *args: Any) -> Optional[asyncpg.Record]:
    pool = get_db_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow(query, *args)


# ---------------------------------------------------------------------------
# Product Queries
# ---------------------------------------------------------------------------

async def fetch_products() -> list[dict[str, Any]]:
    """Fetch all products."""
    rows = await fetch_all(
        "SELECT id, name, description, price, stock_quantity, base_image, "
        "store_id, created_at FROM products ORDER BY created_at DESC"
    )
    return [dict(r) for r in rows]


async def fetch_product_by_id(product_id: str) -> Optional[dict[str, Any]]:
    """Fetch a single product by ID."""
    row = await fetch_one(
        "SELECT id, name, description, price, stock_quantity, base_image, "
        "store_id, created_at FROM products WHERE id = $1",
        product_id,
    )
    return dict(row) if row else None


async def decrement_stock(product_id: str, quantity: int) -> bool:
    """Decrement product stock quantity atomically."""
    result = await execute_returning(
        "UPDATE products SET stock_quantity = stock_quantity - $2 "
        "WHERE id = $1 AND stock_quantity >= $2 RETURNING id",
        product_id, quantity,
    )
    return result is not None


# ---------------------------------------------------------------------------
# Order Queries
# ---------------------------------------------------------------------------

async def create_order(
    customer_email: str,
    total_amount: float,
    shipping_state: str,
    shipping_cost: float,
    payment_reference: str,
    metadata: Optional[dict] = None,
) -> Optional[dict[str, Any]]:
    """Create a new order."""
    import json
    row = await execute_returning(
        "INSERT INTO orders (customer_email, total_amount, shipping_state, "
        "shipping_cost, payment_reference, metadata) "
        "VALUES ($1, $2, $3, $4, $5, $6) "
        "RETURNING id, customer_email, total_amount, shipping_state, "
        "shipping_cost, status, created_at",
        customer_email, total_amount, shipping_state,
        shipping_cost, payment_reference, json.dumps(metadata or {}),
    )
    return dict(row) if row else None


async def create_order_item(
    order_id: str, product_id: str, quantity: int, price: float,
) -> bool:
    """Create an order item."""
    await execute(
        "INSERT INTO order_items (order_id, product_id, quantity, price) "
        "VALUES ($1, $2, $3, $4)",
        order_id, product_id, quantity, price,
    )
    return True


async def fetch_order_by_id(order_id: str) -> Optional[dict[str, Any]]:
    """Fetch a single order by ID."""
    row = await fetch_one(
        "SELECT id, customer_email, total_amount, shipping_state, shipping_cost, "
        "status, payment_reference, metadata, created_at "
        "FROM orders WHERE id = $1",
        order_id,
    )
    return dict(row) if row else None


async def fetch_order_items(order_id: str) -> list[dict[str, Any]]:
    """Fetch all items for an order."""
    rows = await fetch_all(
        "SELECT oi.id, oi.quantity, oi.price, "
        "p.id as product_id, p.name as product_name, p.base_image "
        "FROM order_items oi JOIN products p ON oi.product_id = p.id "
        "WHERE oi.order_id = $1",
        order_id,
    )
    return [dict(r) for r in rows]


async def update_order_status(order_id: str, status: str) -> bool:
    """Update order status."""
    await execute("UPDATE orders SET status = $2 WHERE id = $1", order_id, status)
    return True


# ---------------------------------------------------------------------------
# Shipping Queries
# ---------------------------------------------------------------------------

async def fetch_shipping_cost(state_code: str) -> Optional[dict[str, Any]]:
    """Fetch shipping cost for a Nigerian state."""
    row = await fetch_one(
        "SELECT code, name, shipping_cost, weight_factor "
        "FROM nigerian_states WHERE code = $1",
        state_code,
    )
    return dict(row) if row else None


async def fetch_all_states() -> list[dict[str, Any]]:
    """Fetch all Nigerian states with shipping costs."""
    rows = await fetch_all(
        "SELECT code, name, shipping_cost, weight_factor "
        "FROM nigerian_states ORDER BY name"
    )
    return [dict(r) for r in rows]
