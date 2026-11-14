import json

MANIFEST_PATH = "product-updater/config/shopify_navigation_manifest.json"

with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

beauty_dept = {
    "title": "Beauty & Cosmetics",
    "type": "department",
    "url": "/collections/beauty",
    "items": [
        {
            "title": "Luxury Skincare & Lip Care",
            "type": "category",
            "url": "/collections/skincare",
            "items": [
                {"title": "Shop All Skincare", "url": "/collections/skincare"},
                {"title": "Summer Fridays", "url": "/collections/summer-fridays"},
                {"title": "rhode", "url": "/collections/rhode"},
                {"title": "Gisou", "url": "/collections/gisou"},
                {"title": "Glossier", "url": "/collections/glossier"},
                {"title": "Tower 28 Beauty", "url": "/collections/tower-28"}
            ]
        },
        {
            "title": "Designer Makeup & Complexion",
            "type": "category",
            "url": "/collections/makeup",
            "items": [
                {"title": "Explore Makeup", "url": "/collections/makeup"},
                {"title": "Haus Labs by Lady Gaga", "url": "/collections/haus-labs"},
                {"title": "Westman Atelier", "url": "/collections/westman-atelier"},
                {"title": "PATRICK TA", "url": "/collections/patrick-ta"},
                {"title": "MAKEUP BY MARIO", "url": "/collections/makeup-by-mario"},
                {"title": "Hourglass", "url": "/collections/hourglass"},
                {"title": "Saie", "url": "/collections/saie"},
                {"title": "MERIT", "url": "/collections/merit"},
                {"title": "Kosas", "url": "/collections/kosas"}
            ]
        },
        {
            "title": "Luxury Haircare & Body",
            "type": "category",
            "url": "/collections/haircare",
            "items": [
                {"title": "Explore Hair & Body", "url": "/collections/haircare"},
                {"title": "Gisou Honey Infused", "url": "/collections/gisou"},
                {"title": "Summer Fridays Body", "url": "/collections/summer-fridays"},
                {"title": "REFY Sculpt & Glow", "url": "/collections/refy"},
                {"title": "Glossier Fragrance", "url": "/collections/glossier"}
            ]
        },
        {
            "title": "Value & Gift Sets",
            "type": "category",
            "url": "/collections/beauty-sets",
            "items": [
                {"title": "Shop All Sets", "url": "/collections/beauty-sets"},
                {"title": "Lip Balm & Butter Sets", "url": "/collections/beauty-sets"},
                {"title": "Hydration Travel Kits", "url": "/collections/beauty-sets"},
                {"title": "Dewy Glow Routines", "url": "/collections/beauty-sets"},
                {"title": "Mini Discovery Edits", "url": "/collections/beauty-sets"}
            ]
        }
    ]
}

# Insert Beauty department between Men (index 1) and Brands (index 2)
nav = data.get("navigation", [])
existing_titles = [d.get("title") for d in nav]
if "Beauty & Cosmetics" not in existing_titles:
    nav.insert(2, beauty_dept)

# Also add beauty brands under Brands if not already present
brands_dept = next((d for d in nav if d.get("title") == "Brands"), None)
if brands_dept:
    brand_items = brands_dept.setdefault("items", [])
    existing_brand_titles = {b.get("title") for b in brand_items}
    beauty_brands_to_add = [
        {"title": "Summer Fridays", "url": "/collections/summer-fridays"},
        {"title": "rhode", "url": "/collections/rhode"},
        {"title": "Gisou", "url": "/collections/gisou"},
        {"title": "Haus Labs", "url": "/collections/haus-labs"},
        {"title": "PATRICK TA", "url": "/collections/patrick-ta"},
        {"title": "Westman Atelier", "url": "/collections/westman-atelier"},
        {"title": "Saie", "url": "/collections/saie"},
        {"title": "Hourglass", "url": "/collections/hourglass"},
        {"title": "MERIT", "url": "/collections/merit"},
        {"title": "Kosas", "url": "/collections/kosas"},
        {"title": "Glossier", "url": "/collections/glossier"},
        {"title": "MAKEUP BY MARIO", "url": "/collections/makeup-by-mario"},
        {"title": "REFY", "url": "/collections/refy"},
        {"title": "Tower 28 Beauty", "url": "/collections/tower-28"}
    ]
    for bb in beauty_brands_to_add:
        if bb["title"] not in existing_brand_titles:
            brand_items.append(bb)

with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("Updated shopify_navigation_manifest.json with Beauty & Cosmetics department and 14 beauty brands!")
