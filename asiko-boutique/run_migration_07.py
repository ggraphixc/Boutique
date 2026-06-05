#!/usr/bin/env python3
"""ASIKO Boutique — Migration 07: 3D GLTF Asset Columns

Usage:
    python run_migration_07.py

Reads DATABASE_URL from .env and executes supabase/migrations/07_gltf_columns.sql.
"""

import os
import sys
from pathlib import Path

# Load .env from project root
from dotenv import load_dotenv

load_dotenv()

import asyncpg


def main():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("[ERROR] DATABASE_URL not found in environment or .env file.")
        print("       Ensure .env is configured before running this script.")
        sys.exit(1)

    sql_path = Path(__file__).resolve().parent / "supabase" / "migrations" / "07_gltf_columns.sql"
    if not sql_path.exists():
        print(f"[ERROR] Migration file not found: {sql_path}")
        sys.exit(1)

    sql = sql_path.read_text(encoding="utf-8")

    async def run():
        conn = await asyncpg.connect(dsn=database_url)
        try:
            print("[MIGRATION 07] Executing 07_gltf_columns.sql ...")
            await conn.execute(sql)
            print("[MIGRATION 07] Completed successfully.")
        except Exception as e:
            print(f"[MIGRATION 07 ERROR] {e}")
            sys.exit(1)
        finally:
            await conn.close()

    import asyncio
    asyncio.run(run())


if __name__ == "__main__":
    main()
