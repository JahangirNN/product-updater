with open('theme/assets/theme.js', 'r', encoding='utf-8') as f:
    text = f.read()

import re
pos = text.find('class Delegate')
if pos != -1:
    print(text[pos:pos+1500])
else:
    pos = text.find('function Delegate')
    if pos != -1:
        print(text[pos:pos+1500])
    else:
        # find where Delegate is defined
        for m in re.finditer(r'Delegate\s*=', text):
            p = m.start()
            print(text[p-50:p+500])
