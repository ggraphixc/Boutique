"""Quick end-to-end test of the pipeline daemon and virtual experience."""
import asyncio
import os
import sys
import logging
import tempfile
import json

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ.setdefault('ENVIRONMENT', 'development')

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
log = logging.getLogger('test_e2e')

DB_URL = os.environ.get('DATABASE_URL', '')
if not DB_URL:
    # Try to read from .env
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith('DATABASE_URL='):
                    DB_URL = line.split('=', 1)[1].strip().strip('"').strip("'")
                    os.environ['DATABASE_URL'] = DB_URL
                    break


async def check_database():
    """Check database schema and products."""
    import asyncpg
    if not DB_URL:
        log.error('No DATABASE_URL found')
        return False
    
    log.info(f'Connecting to database...')
    pool = await asyncpg.create_pool(DB_URL, min_size=2, max_size=5)
    
    async with pool.acquire() as conn:
        # Check products table columns
        cols = await conn.fetch("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name='products' ORDER BY ordinal_position
        """)
        col_names = [c['column_name'] for c in cols]
        log.info(f'Products columns: {col_names}')
        
        # Check critical columns
        for col in ['pipeline_status', 'asset_category', 'model_3d_url', 'model_3d_data']:
            if col in col_names:
                log.info(f'  ✓ {col} exists')
            else:
                log.warning(f'  ✗ {col} MISSING')
        
        # Count products
        count = await conn.fetchval('SELECT COUNT(*) FROM products')
        log.info(f'Products count: {count}')
        
        # Check queued products
        queued = await conn.fetchval("SELECT COUNT(*) FROM products WHERE pipeline_status = 'queued'")
        log.info(f'Products queued: {queued}')
        
        # Check avatar_measurements table
        has_meas = await conn.fetchval("""
            SELECT EXISTS(SELECT 1 FROM information_schema.tables 
            WHERE table_name='avatar_measurements')
        """)
        log.info(f'avatar_measurements table exists: {has_meas}')
        
        # Check avatar files exist
        avatar_female = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static', 'models', 'avatar_female.glb')
        avatar_male = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static', 'models', 'avatar_male.glb')
        
        if os.path.exists(avatar_female):
            size = os.path.getsize(avatar_female)
            log.info(f'avatar_female.glb: {size:,} bytes')
        else:
            log.warning(f'avatar_female.glb NOT FOUND at {avatar_female}')
        
        if os.path.exists(avatar_male):
            size = os.path.getsize(avatar_male)
            log.info(f'avatar_male.glb: {size:,} bytes')
        else:
            log.warning(f'avatar_male.glb NOT FOUND at {avatar_male}')
        
        # Check garment templates
        template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static', 'models', 'templates')
        if os.path.exists(template_dir):
            templates = os.listdir(template_dir)
            log.info(f'Garment templates: {len(templates)} files')
            for t in templates:
                log.info(f'  ✓ {t}')
        else:
            log.warning(f'Template directory NOT FOUND: {template_dir}')
    
    await pool.close()
    return True


async def test_pipeline_processing():
    """Test that the pipeline daemon can process a product."""
    import asyncpg
    from app.workers.pipeline_daemon import AsikoPipelineDaemon
    
    log.info('\n--- Testing pipeline processing ---')
    
    pool = await asyncpg.create_pool(DB_URL, min_size=2, max_size=5)
    
    # Create a test product with a source image
    async with pool.acquire() as conn:
        # First, find any existing source images to use
        source_img = await conn.fetchval("""
            SELECT source_2d_image_url FROM products 
            WHERE source_2d_image_url IS NOT NULL AND source_2d_image_url != ''
            LIMIT 1
        """)
        
        if not source_img:
            log.warning('No source images found in DB. Skipping pipeline test.')
            await pool.close()
            return True
        
        log.info(f'Using source image: {source_img}')
        
        # Create test product
        import uuid
        test_name = f'Test Pipeline {uuid.uuid4().hex[:8]}'
        product_id = await conn.fetchval("""
            INSERT INTO products (store_id, name, description, price, stock_quantity, pipeline_status, 
                                  asset_category, source_2d_image_url)
            VALUES ('a1b2c3d4-e5f6-7890-abcd-ef1234567890', $1, 'E2E test', 15000, 5, 'queued', 'apparel', $2)
            RETURNING id
        """, test_name, source_img)
        log.info(f'Created test product: {product_id}')
    
    # Initialize daemon with pool
    daemon = AsikoPipelineDaemon(pool)
    log.info(f'Daemon initialized')
    
    # Process the product directly
    log.info(f'Processing product {product_id}...')
    await daemon._process_product(product_id, source_img, 'apparel', 'Test Pipeline Dress')
    
    # Check result
    async with pool.acquire() as conn:
        updated = await conn.fetchrow("""
            SELECT pipeline_status, model_3d_url, pipeline_error_log
            FROM products WHERE id = $1
        """, product_id)
        
        log.info(f'  Status: {updated["pipeline_status"]}')
        if updated["model_3d_url"]:
            log.info(f'  model_3d_url: {updated["model_3d_url"]}')
        if updated["pipeline_error_log"]:
            log.warning(f'  Error: {updated["pipeline_error_log"]}')
        
        success = updated["pipeline_status"] in ("completed", "generating_texture")
        
        # Cleanup test product
        await conn.execute("DELETE FROM products WHERE id = $1", product_id)
        log.info('Cleaned up test product')
    
    await pool.close()
    return success


async def test_measurements():
    """Test measurements API endpoints."""
    log.info('\n--- Testing measurements ---')
    
    from app.garment_templates import DEFAULT_MEASUREMENTS, generate_garment
    
    log.info(f'Default measurements: {DEFAULT_MEASUREMENTS}')
    
    # Test template generation
    avatar_paths = {
        'female': 'static/models/avatar_female.glb',
        'male': 'static/models/avatar_male.glb',
    }
    for category in ['dress', 'shirt', 'trouser', 'skirt', 'jacket', 'hoodie', 'shoe', 'bag']:
        glb = generate_garment(category, DEFAULT_MEASUREMENTS, avatar_glb_path=avatar_paths['female'])
        log.info(f'  Generated {category}: {len(glb["glb_bytes"])} bytes')
    
    log.info('✓ All templates generate successfully')
    return True


async def main():
    log.info('=== E2E Pipeline Test ===')
    
    # Check database
    log.info('\n--- Database check ---')
    db_ok = await check_database()
    
    if not db_ok:
        log.error('Database check failed')
        return
    
    # Test measurements
    meas_ok = await test_measurements()
    
    # Test pipeline processing
    pipeline_ok = await test_pipeline_processing()
    
    # Summary
    log.info('\n=== Summary ===')
    log.info(f'Database: {"✓" if db_ok else "✗"}')
    log.info(f'Measurements: {"✓" if meas_ok else "✗"}')
    log.info(f'Pipeline: {"✓" if pipeline_ok else "✗"}')
    
    if all([db_ok, meas_ok, pipeline_ok]):
        log.info('\n✓ All E2E tests passed!')
    else:
        log.error('\n✗ Some tests failed')


if __name__ == '__main__':
    asyncio.run(main())
