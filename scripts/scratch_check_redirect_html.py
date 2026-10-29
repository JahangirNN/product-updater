import urllib.request
import urllib.error

req = urllib.request.Request('https://therareavenue.com/collections/watches', headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        html = resp.read().decode('utf-8')
        code = resp.status
except urllib.error.HTTPError as e:
    html = e.read().decode('utf-8')
    code = e.code

print("HTTP Status:", code)
print("meta refresh in HTML?", 'http-equiv="refresh"' in html)
print("script in HTML?", 'location.replace("/collections/luxury-watches' in html)
if 'http-equiv="refresh"' in html:
    print([line for line in html.splitlines() if 'http-equiv="refresh"' in line])
