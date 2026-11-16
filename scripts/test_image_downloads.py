import requests

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
}

test_urls = {
    'jomashop': 'https://cdn2.jomashop.com/media/catalog/product/t/i/tissot-chemin-des-tourelles-mother-of-pearl-silver-dial-automatic-ladies-watch-t099.207.22.118.02.jpg',
    'jwpei': 'https://cdn.shopify.com/s/files/1/0150/6292/5412/files/sxs5gs2h9v.jpg?v=1786501927',
    'sephora': 'https://www.sephora.com/productimages/sku/s2029841-main-zoom.jpg'
}

for store, u in test_urls.items():
    try:
        r = requests.get(u, headers=headers, timeout=10)
        ct = r.headers.get("content-type")
        print(f"{store}: status={r.status_code}, content-type={ct}, bytes={len(r.content)}")
    except Exception as e:
        print(f"{store}: error={e}")
