import asyncio, asyncpg, os
from dotenv import load_dotenv
load_dotenv()

async def main():
    dsn = os.getenv('DATABASE_URL')
    conn = await asyncpg.connect(dsn)
    await conn.execute("ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS notif_new_order BOOLEAN NOT NULL DEFAULT TRUE")
    await conn.execute("ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS notif_pipeline BOOLEAN NOT NULL DEFAULT TRUE")
    await conn.execute("ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS notif_review BOOLEAN NOT NULL DEFAULT TRUE")
    await conn.execute("ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS notif_low_stock BOOLEAN NOT NULL DEFAULT TRUE")
    await conn.execute("ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS chatbot_enabled BOOLEAN NOT NULL DEFAULT TRUE")
    await conn.execute("ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS chatbot_welcome TEXT NOT NULL DEFAULT 'Hi! I am your personal ASIKO stylist. How can I help you find the perfect look today?'")
    await conn.execute("ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS chatbot_color_primary VARCHAR(20) NOT NULL DEFAULT '#0D2A22'")
    await conn.execute("ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS chatbot_color_accent VARCHAR(20) NOT NULL DEFAULT '#D4AF37'")
    await conn.execute("ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS blog_enabled BOOLEAN NOT NULL DEFAULT TRUE")
    await conn.execute("ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS blog_posts_per_page INT NOT NULL DEFAULT 6")
    print('All missing columns added successfully')
    await conn.close()

asyncio.run(main())
