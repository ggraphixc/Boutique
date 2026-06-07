import re
with open('app/templates/admin/base.html','r',encoding='utf-8') as f:
    src = f.read()
pat = re.compile(r'(<button[^>]*id="nav-[a-z\-]+"[^>]*>.*?</button>)', re.S)
matches = pat.findall(src)
for i, m in enumerate(matches, 1):
    print(f'--- match {i} ---')
    print(m[:300])
    print('...' if len(m) > 300 else '')
    print()
