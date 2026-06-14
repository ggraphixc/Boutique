import asyncio
import os
import sys

sys.path.insert(0, "C:/Users/USER/Documents/GitHub/Boutique/asiko-boutique")
from dotenv import load_dotenv
load_dotenv()
import asyncpg

async def migrate():
    pool = await asyncpg.create_pool(dsn=os.environ["DATABASE_URL"], min_size=1, max_size=2)
    sql_path = os.path.join(os.path.dirname(__file__), "..", "database", "migrations", "13_avatar_measurements.sql")
    with open(sql_path) as f:
        sql = f.read()
    async with pool.acquire() as conn:
        await conn.execute(sql)
        print("Migration 13 applied successfully")
        exists = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='avatar_measurements')"
        )
        print(f"Table exists: {exists}")
    await pool.close()

asyncio.run(migrate())
