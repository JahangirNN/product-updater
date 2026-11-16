import requests

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
}

u = 'https://cdn2.jomashop.com/media/catalog/product/t/i/tissot-chemin-des-tourelles-automatic-mother-of-pearl-dial-ladies-watch-t099-207-22-118-02-t0992072211802.jpg'
r = requests.get(u, headers=headers, timeout=10)
print(f"Jomashop live image status={r.status_code}, content-type={r.headers.get('content-type')}, bytes={len(r.content)}")
