import httpx
import re

client = httpx.Client(follow_redirects=True, timeout=15.0)

for url_path in ["/collections/womens-handbags/coach", "/collections/womens-handbags/shoulder-bags"]:
    r = client.get("https://therareavenue.com" + url_path)
    # Find product list or main section
    print(f"=== {url_path} ===")
    matches = re.findall(r'<product-list[\s\S]*?</product-list>', r.text)
    if matches:
        print("Product-list snippet:", matches[0][:500])
    else:
        # search for collections section
        m2 = re.findall(r'id="main"[\s\S]*?</main>', r.text)
        if m2:
            print("Main snippet:", m2[0][:500])
        else:
            print("No main or product-list found. Page length:", len(r.text))
