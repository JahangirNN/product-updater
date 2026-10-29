with open('theme/assets/theme.js', 'r', encoding='utf-8') as f:
    text = f.read()

import re
matches = re.findall(r'_delegate\d*\)\.on\([^)]+\)', text)
for m in matches:
    print(m)
