import os
p = os.path.join(r'C:\workspace\dropship-scraper-portable-20260905\product-updater\horizon_clean_theme\snippets\header-drawer.liquid')
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

target = 'class="menu-drawer__featured-content"'
replacement = 'class="menu-drawer__featured-content" style="margin-top: 1.25rem; padding-top: 0.85rem; border-top: 1px solid rgba(0,0,0,0.06);"'
if target in c:
    c = c.replace(target, replacement, 1)

target2 = '<ul class="menu-drawer__featured-content-list menu-drawer__animated-element list-unstyled">'
replacement2 = '<div style="padding: 0 1.25rem 0.5rem; font-size: 0.6875rem; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: #8c827a;">Featured Curations</div>\n          ' + target2
if target2 in c:
    c = c.replace(target2, replacement2, 1)

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)
print('Updated featured-content header successfully')
