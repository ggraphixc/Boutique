#!/usr/bin/env python3
"""ASIKO Boutique — Consolidated Migration Runner

Runs all migrations 01–07 in order against the Neon PostgreSQL database.
Reads DATABASE_URL from .env.

Usage:
    python run_migration_all.py
"""

import os
import sys
import asyncio
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import asyncpg


MIGRATIONS_DIR = Path(__file__).resolve().parent / "supabase" / "migrations"

MIGRATION_ORDER = [
    "01_init_schema.sql",
    "02_reservations.sql",
    "03_waitlist.sql",
    "04_luxury_core.sql",
    "05_single_brand.sql",
    "06_schema_alignment.sql",
    "07_gltf_columns.sql",
]


async def run_migration(conn, filename: str) -> None:
    path = MIGRATIONS_DIR / filename
    if not path.exists():
        print(f"  ⚠  {filename} — file not found, skipping.")
        return
    sql = path.read_text(encoding="utf-8")
    print(f"  ▶  Running {filename} ...")
    await conn.execute(sql)
    print(f"  ✓  {filename}")


async def main():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("[ERROR] DATABASE_URL not found. Ensure .env is configured.")
        sys.exit(1)

    print("ASIKO Boutique — Consolidated Migration Runner")
    print(f"  Directory: {MIGRATIONS_DIR}")
    print(f"  Migrations: {len(MIGRATION_ORDER)} files")
    print()

    conn = await asyncpg.connect(dsn=database_url)
    try:
        for migration in MIGRATION_ORDER:
            await run_migration(conn, migration)
        print("\nAll migrations completed successfully.")
    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        sys.exit(1)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
