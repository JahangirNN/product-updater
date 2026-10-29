import re

with open('header_dump_768.html', 'r', encoding='utf-8') as f:
    content = f.read()

sections = re.findall(r'id="shopify-section-[^"]+"', content)
print('Shopify sections in header group:', sections)

# Find header tags and layout
for m in re.finditer(r'<header-component[^>]*>', content):
    print('Header component:', m.group(0))

for m in re.finditer(r'<header[^>]*>', content):
    print('Header tag:', m.group(0)[:200])

# Find all direct child divs of header__columns or header__row
for m in re.finditer(r'<div class="header__column[^"]*"[^>]*>', content):
    print('Header column:', m.group(0))

for m in re.finditer(r'<div class="header__drawer[^"]*"[^>]*>', content):
    print('Header drawer container:', m.group(0))

for m in re.finditer(r'<header-menu[^>]*>', content):
    print('Header menu tag:', m.group(0))

for m in re.finditer(r'<header-actions[^>]*>', content):
    print('Header actions tag:', m.group(0))
