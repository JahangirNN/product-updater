with open('header_dump_768.html', 'r', encoding='utf-8') as f:
    html = f.read()

import re

# Find all stylesheet tags in header
stylesheets = re.findall(r'<style[^>]*>([\s\S]*?)</style>', html)
print(f"Found {len(stylesheets)} style tags in header dump.")

# Find any media queries
for i, s in enumerate(stylesheets):
    media = re.findall(r'@media[^{]+{[^{}]+{[^{}]+}}', s)
    if media:
        print(f"Style tag {i} media queries:", media[:5])

# Print the main header component HTML structure (first 2000 chars)
h_start = html.find('<header-component')
print(html[h_start:h_start+2500])
