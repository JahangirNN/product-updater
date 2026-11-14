from curl_cffi import requests

url = 'https://www.sephora.com/product/hair-body-fragrance-mist-vanilla-P525593'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}
r = requests.get(url, headers=headers, impersonate='chrome124', timeout=20)
print('Status:', r.status_code, 'Length:', len(r.text))
if 'regularChildSkus' in r.text:
    print('Found regularChildSkus')
elif '{"page":' in r.text:
    print('Found page JSON')
else:
    print('Snippet:', r.text[:300])
