import os
import sys
import json
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from scripts.audit_luxury_bags_catalog import get_luxury_bag_products

def resolve_clean_bag_material(prod, title):
    specs = prod.get("specifications") or {}
    raw_material = specs.get("Material") or specs.get("Main Material") or specs.get("Major Material") or prod.get("material") or ""
    raw_mat_str = str(raw_material).strip()
    
    if "tanneries receiving" in raw_mat_str.lower() or "leather in this product" in raw_mat_str.lower() or len(raw_mat_str) > 80:
        bullets = specs.get("DetailsBullets") or []
        for b in bullets:
            b_str = str(b).strip()
            b_low = b_str.lower()
            if any(k in b_low for k in ["nubuck", "pebbled leather", "saffiano", "crossgrain", "calf leather", "smooth leather", "nappa", "suede"]):
                return b_str
            if "100% leather" in b_low:
                return "100% Refined Leather"
            if "canvas" in b_low:
                return "Durable Luxury Canvas"
        
        title_low = title.lower()
        if "nubuck" in title_low:
            return "Premium Nubuck Leather"
        if "pebbled leather" in title_low:
            return "Pebbled Leather"
        if "saffiano" in title_low:
            return "Saffiano Leather"
        if "leather" in title_low:
            return "LWG Certified Leather"
        if "canvas" in title_low:
            return "Signature Coated Canvas"
        return "LWG Certified Leather"
        
    if raw_mat_str and raw_mat_str.lower() != title.strip().lower() and not raw_mat_str.lower().startswith("http"):
        return raw_mat_str
        
    title_low = title.lower()
    if "signature canvas" in title_low:
        return "Signature Coated Canvas"
    if "pebbled leather" in title_low:
        return "Pebbled Leather"
    if "saffiano" in title_low:
        return "Saffiano Leather"
    if "leather" in title_low:
        return "Refined Calf Leather"
    if "suede" in title_low:
        return "Premium Suede"
    if "canvas" in title_low:
        return "Durable Luxury Canvas"
    if "nylon" in title_low:
        return "Technical Luxury Nylon"
    if prod.get("source_store") == "jwpei":
        return "Vegan Leather"
    return "Refined Leather"

catalog = get_luxury_bag_products()
samples = []
for brand, prods in catalog.items():
    for p in prods[:10]:
        t = p.get("title", "")
        mat = resolve_clean_bag_material(p, t)
        samples.append((brand, t[:30], mat))

for b, t, m in samples:
    print(f"[{b:11}] {t:32} -> {m}")
