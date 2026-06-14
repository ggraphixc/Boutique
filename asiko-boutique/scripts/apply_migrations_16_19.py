import asyncio, os
from dotenv import load_dotenv
import asyncpg

MIGRATIONS = [
    '16_analytics_tracking.sql',
    '17_logistics.sql',
    '18_social_commerce.sql',
    '19_loyalty_system.sql',
]

async def main():
    load_dotenv()
    url = os.getenv('DATABASE_URL')
    if not url:
        print('DATABASE_URL not set')
        return
    conn = await asyncpg.connect(url)
    for m in MIGRATIONS:
        path = f'database/migrations/{m}'
        with open(path) as f:
            sql = f.read()
        await conn.execute(sql)
        print(f'Applied: {m}')
    print('\nAll tables:')
    tables = await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
    for t in tables:
        print(f'  {t["tablename"]}')
    await conn.close()

asyncio.run(main())
