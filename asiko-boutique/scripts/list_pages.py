import asyncio, asyncpg, os
from dotenv import load_dotenv
load_dotenv()

async def main():
    dsn = os.getenv('DATABASE_URL')
    conn = await asyncpg.connect(dsn)
    rows = await conn.fetch('SELECT id, title, slug, show_in_nav, show_in_footer, is_live FROM custom_pages ORDER BY sort_order')
    for r in rows:
        rid = str(r['id'])[:8]
        title = r['title']
        slug = r['slug']
        nav = r['show_in_nav']
        footer = r['show_in_footer']
        live = r['is_live']
        print(f'{rid}... | {title} | {slug} | nav={nav} | footer={footer} | live={live}')
    await conn.close()

asyncio.run(main())
