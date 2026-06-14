import asyncio, asyncpg, os
from dotenv import load_dotenv
load_dotenv()

async def main():
    dsn = os.getenv('DATABASE_URL')
    conn = await asyncpg.connect(dsn)
    rows = await conn.fetch(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'store_settings' ORDER BY ordinal_position"
    )
    cols = [r['column_name'] for r in rows]
    checks = ['notif_new_order', 'notif_pipeline', 'notif_review', 'notif_low_stock',
              'admin_auth', 'session_timeout', 'chatbot_enabled', 'chatbot_welcome',
              'chatbot_color_primary', 'chatbot_color_accent', 'blog_enabled', 'blog_posts_per_page']
    for c in checks:
        status = 'EXISTS' if c in cols else 'MISSING'
        print(f'{c}: {status}')
    await conn.close()

asyncio.run(main())
