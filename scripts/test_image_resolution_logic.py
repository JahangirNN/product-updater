import os
import sys
import glob
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_taxonomy import resolve_product_type, resolve_luxury_bag_silhouette

BROKEN_IMAGE_URLS = {
    "https://cdn.shopify.com/s/files/1/0150/6292/5412/files/1782552557039-gd2lat73iko.jpg?v=1787122998",
    "https://cdn.shopify.com/s/files/1/0150/6292/5412/files/134kzy7p88va.jpg?v=1787110927",
    "https://cdn.shopify.com/s/files/1/0150/6292/5412/files/ecakemkflg.jpg?v=1787110927",
    "https://cdn.shopify.com/s/files/1/0150/6292/5412/files/tdhylr3bfiq.jpg?v=1787110927",
    "https://cdn.shopify.com/s/files/1/0150/6292/5412/files/217vl4kap0i.jpg?v=1785915162",
    "https://cdn.shopify.com/s/files/1/0150/6292/5412/files/nn2mso31ce.jpg?v=1787726550",
    "https://cdn.shopify.com/s/files/1/0150/6292/5412/files/ezxi6l13hhq.jpg?v=1786681327",
    "https://cdn.shopify.com/s/files/1/0150/6292/5412/files/fi5argg4jxo.jpg?v=1787726527",
    "https://cdn.shopify.com/s/files/1/0150/6292/5412/files/n8evxuddn6b.jpg?v=1787726573",
    "https://cdn.shopify.com/s/files/1/0150/6292/5412/files/7nej3cp864a.jpg?v=1787727726",
    "https://cdn.shopify.com/s/files/1/0150/6292/5412/files/znibcgv7p4.jpg?v=1787726574",
    "https://cdn.shopify.com/s/files/1/0150/6292/5412/files/hp5ph3z4154.jpg?v=1787727127",
    "https://cdn.shopify.com/s/files/1/0150/6292/5412/files/h2u8duy3pj.jpg?v=1787727150",
    "https://cdn.shopify.com/s/files/1/0150/6292/5412/files/1781236230586-vehklaex1ve.jpg?v=1783497127",
    "https://cdn.shopify.com/s/files/1/0150/6292/5412/files/1781242424362-r84wns0a4r.jpg?v=1783496551",
    "https://cdn.shopify.com/s/files/1/0150/6292/5412/files/1781775680803-ucfqb49e50c.jpg?v=1786517597",
    "https://cdn.shopify.com/s/files/1/0150/6292/5412/files/1773380534033-rk47ecahgw.jpg?v=1773387755",
    "https://cdn.shopify.com/s/files/1/0150/6292/5412/files/1773380505326-uhmm4qxo338.jpg?v=1773387755",
}

def resolve_variant_image_test(v, prod):
    raw_img = v.get("image_url") or v.get("image") or (v.get("images") or [None])[0]
    if raw_img and isinstance(raw_img, str) and raw_img.startswith("http") and raw_img not in BROKEN_IMAGE_URLS:
        return raw_img

    gallery = prod.get("images") or []
    color_name = str(v.get("color") or v.get("title") or "").strip().lower()
    sku = str(v.get("sku") or "").strip().lower()

    if sku and len(sku) > 3:
        for g_img in gallery:
            if isinstance(g_img, str) and sku in g_img.lower() and g_img not in BROKEN_IMAGE_URLS:
                return g_img

    if color_name and color_name not in ("default", "default title", "standard", "one size"):
        clean_slugs = [
            color_name.replace(" ", "-"),
            color_name.replace(" ", "_"),
            color_name.replace("/", "-"),
            color_name.replace("/", "_")
        ]
        for g_img in gallery:
            if not isinstance(g_img, str) or g_img in BROKEN_IMAGE_URLS:
                continue
            g_lower = g_img.lower()
            if any(s in g_lower for s in clean_slugs if len(s) > 2):
                return g_img

    variants_raw = prod.get("variants") or []
    if len(variants_raw) <= 1:
        for g_img in gallery:
            if isinstance(g_img, str) and g_img.startswith("http") and g_img not in BROKEN_IMAGE_URLS:
                return g_img
        primary = prod.get("image") or prod.get("image_url")
        if primary and isinstance(primary, str) and primary.startswith("http") and primary not in BROKEN_IMAGE_URLS:
            return primary

    return None

# Test on aria shoulder bag
with open(os.path.join(PROJECT_ROOT, "storage", "db", "jwpei", "products", "0127b80a068c75d4.json"), "r", encoding="utf-8") as f:
    aria = json.load(f)

print("Aria variants count before:", len(aria.get("variants", [])))
valid_aria = []
for v in aria.get("variants", []):
    img = resolve_variant_image_test(v, aria)
    if img:
        valid_aria.append((v.get("title"), img))
    else:
        print(f"  PRUNED GHOST VARIANT: {v.get('title')}")

print(f"Aria variants count after: {len(valid_aria)} (All valid with image: {len(valid_aria) == len(aria.get('variants', [])) - 1})")

# Test on Coach Teri Mini Crossbody
with open(os.path.join(PROJECT_ROOT, "storage", "db", "coach", "products", "0f73f4eea686b114.json"), "r", encoding="utf-8") as f:
    coach_teri = json.load(f)
valid_coach = [v for v in coach_teri.get("variants", []) if resolve_variant_image_test(v, coach_teri)]
print(f"Coach Teri variants: {len(coach_teri.get('variants', []))} -> Valid with image: {len(valid_coach)}")

# Test on a Jomashop watch
with open(glob.glob(os.path.join(PROJECT_ROOT, "storage", "db", "jomashop", "products", "*.json"))[0], "r", encoding="utf-8") as f:
    watch = json.load(f)
watch_vars = watch.get("variants") or [{}]
valid_watch = [v for v in watch_vars if resolve_variant_image_test(v, watch)]
print(f"Jomashop watch variants: {len(watch_vars)} -> Valid with image: {len(valid_watch)} -> Img: {valid_watch[0] if valid_watch else None}")
