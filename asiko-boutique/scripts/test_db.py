import os, re, asyncio, time
from pathlib import Path

for line in Path(".env").read_text().splitlines():
    line = line.strip()
    if not line or line.startswith("#"):
        continue
    m = re.match(r'^([A-Z_][A-Z0-9_]*)=(.*)$', line)
    if m:
        os.environ[m.group(1)] = m.group(2).strip('"')

import sys
sys.path.insert(0, ".")
from app.database import init_db_pool, close_db_pool


async def go():
    t0 = time.time()
    try:
        pool = await asyncio.wait_for(init_db_pool(), timeout=45)
        print(f"Pool OK in {time.time()-t0:.2f}s, size={pool.get_size()}/{pool.get_max_size()}", flush=True)
        # Sanity-check a query
        v = await pool.fetchval("SELECT 1")
        print(f"Query OK, value={v}", flush=True)
        await close_db_pool()
    except Exception as e:
        print(f"FAIL in {time.time()-t0:.2f}s: {type(e).__name__}: {str(e)[:300]}", flush=True)


asyncio.run(go())
