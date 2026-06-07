import re
with open('app/templates/admin/base.html','r',encoding='utf-8') as f:
    src = f.read()

# Find every nav-item block
pattern = re.compile(r'<button[^>]*id="(nav-[a-z\-]+)"[^>]*>.*?<span class="nav-label">([^<]+)</span>(?:\s*<span[^>]*class="nav-badge[^"]*"[^>]*>\s*(\d+))?', re.S)
for m in pattern.finditer(src):
    nav_id, label, badge = m.group(1), m.group(2), m.group(3) or ''
    print(f'{nav_id:18s}  label={label!r:18s}  badge={badge}')

print('\n--- PAGE_META ---')
for m in re.finditer(r"'nav-([a-z\-]+)':\s*\{[^}]*title:\s*'([^']+)'", src):
    print(f'  nav-{m.group(1):18s}  title={m.group(2)}')

print('\n--- idMap ---')
for m in re.finditer(r"'([a-z\-]+)':\s*'(nav-[a-z\-]+)'", src):
    print(f'  slug={m.group(1):18s}  -> {m.group(2)}')
