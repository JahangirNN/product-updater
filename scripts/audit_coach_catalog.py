"""
Coach Catalog Quality Audit (Tier A & Tier B)
Executes 100% static validation on all 570 Coach products and deep live parity check on 20 random samples.
Pure functional composition, zero classes (ADR 0005).
"""
import os
import sys
import json
import random
import re
import hashlib
import time
from typing import Dict, Any, List, Tuple
import httpx

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.getcwd())

from storage.network import get_browser_headers, create_http_client
from storage.forex import get_usd_to_inr_rate

PRODUCTS_DIR = "storage/db/coach/products"


def run_tier_a_static_audit() -> Dict[str, Any]:
    """Audit 100% of local product JSON files."""
    print("========================================================")
    print("Executing Phase 3 - Tier A: Full Static Catalog Audit")
    print("========================================================")

    files = [f for f in os.listdir(PRODUCTS_DIR) if f.endswith(".json")]
    total = len(files)
    print(f"[*] Total files in {PRODUCTS_DIR}: {total}")

    pk_failures = []
    accordion_failures = []
    image_failures = []
    currency_failures = []
    category_leaks = []
    footwear_size_failures = []

    # Accurate word-boundary check for apparel
    apparel_pattern = re.compile(r'\b(?:dresses?|skirts?|jackets?|coats?|pants?|sweaters?|hoodies?|t-shirts?)\b', re.IGNORECASE)

    for fname in files:
        fpath = os.path.join(PRODUCTS_DIR, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            p = json.load(f)

        pid = p.get("product_id")
        sku = p.get("source_sku", "").strip()

        # 1. Primary Key SHA256 Check
        expected_pid = hashlib.sha256(f"coach::{sku}".encode("utf-8")).hexdigest()[:16]
        if pid != expected_pid:
            pk_failures.append((fname, pid, expected_pid))

        # 2. Accordion Check
        desc_html = p.get("descriptionHtml", "")
        if "size-guide-accordion" not in desc_html:
            accordion_failures.append(fname)

        # 3. Image URLs Check
        images = p.get("images", [])
        if not images or not all(img.startswith("https://coach.scene7.com") for img in images):
            image_failures.append(fname)

        # 4. Currency Math Check
        sp = float(p.get("source_price") or 0.0)
        rate = float(p.get("forex_rate_used") or 95.6)
        cp = float(p.get("current_price") or 0.0)
        if sp > 0 and abs(cp - round(sp * rate)) > 1.0:
            currency_failures.append((fname, sp, rate, cp, round(sp * rate)))

        # 5. Category Leak Check (Reject dresses, apparel, coats)
        title = p.get("title", "")
        if apparel_pattern.search(title):
            category_leaks.append((fname, title))

        # 6. Footwear Size Variants Check
        ptype = p.get("product_type", "")
        if ptype == "Shoes & Footwear":
            variants = p.get("variants", [])
            if len(variants) < 2 or not all("US " in v.get("title", "") for v in variants):
                footwear_size_failures.append((fname, len(variants)))

    print(f"  [1] Primary Key SHA256 Validity: {total - len(pk_failures)}/{total} Pass (Failures: {len(pk_failures)})")
    print(f"  [2] Size Guide Accordion Present: {total - len(accordion_failures)}/{total} Pass (Failures: {len(accordion_failures)})")
    print(f"  [3] Scene7 High-Res Media URLs:  {total - len(image_failures)}/{total} Pass (Failures: {len(image_failures)})")
    print(f"  [4] Whole-Rupee INR Currency Math: {total - len(currency_failures)}/{total} Pass (Failures: {len(currency_failures)})")
    print(f"  [5] Category Isolation (0 Leaks): {total - len(category_leaks)}/{total} Pass (Leaks: {len(category_leaks)})")
    print(f"  [6] Footwear Granular Sizing:     {total - len(footwear_size_failures)}/{total} Pass (Failures: {len(footwear_size_failures)})")

    tier_a_pass = (
        len(pk_failures) == 0 and
        len(accordion_failures) == 0 and
        len(image_failures) == 0 and
        len(currency_failures) == 0 and
        len(category_leaks) == 0 and
        len(footwear_size_failures) == 0
    )

    print(f"\n[*] Tier A Audit Result: {'100% PASS' if tier_a_pass else 'FAILED'}")
    return {
        "tier_a_pass": tier_a_pass,
        "total_audited": total,
        "pk_failures": pk_failures,
        "accordion_failures": accordion_failures,
        "image_failures": image_failures,
        "currency_failures": currency_failures,
        "category_leaks": category_leaks,
        "footwear_size_failures": footwear_size_failures
    }


def parse_live_pdp_for_sku(html_text: str, target_sku: str) -> Dict[str, Any]:
    """Extract accurate live price, stock, and sizes for the specific target SKU."""
    json_lds = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html_text, re.DOTALL)
    
    product_single = {}
    product_group = {}
    for block in json_lds:
        try:
            d = json.loads(block)
            t = d.get("@type")
            if t == "Product":
                product_single = d
            elif t == "ProductGroup":
                product_group = d
        except Exception:
            pass

    price = None
    offers = (product_single or {}).get("offers", {})
    if isinstance(offers, list) and offers:
        offers = offers[0]
    if isinstance(offers, dict):
        if offers.get("price"):
            price = float(offers["price"])
        elif offers.get("lowPrice"):
            price = float(offers["lowPrice"])

    clean_target = target_sku.strip()
    if product_group and "hasVariant" in product_group:
        for v in product_group["hasVariant"]:
            v_sku = str(v.get("sku", "")).strip()
            if v_sku == clean_target:
                v_offers = v.get("offers", {})
                if isinstance(v_offers, list) and v_offers:
                    v_offers = v_offers[0]
                if isinstance(v_offers, dict) and v_offers.get("price"):
                    price = float(v_offers["price"])
                    break

    in_stock = False
    if product_single and "offers" in product_single:
        o = product_single["offers"]
        if isinstance(o, list) and o:
            o = o[0]
        if "InStock" in str(o.get("availability", "")):
            in_stock = True

    size_buttons = re.findall(r'<button[^>]*class="[^"]*variation-size[^"]*"[^>]*data-qa="([^"]+)"[^>]*>([^<]+)</button>', html_text)
    shoe_sizes = {}
    if size_buttons:
        for qa, sz in size_buttons:
            s_clean = sz.strip()
            s_avail = "enbld" in qa.lower()
            shoe_sizes[s_clean] = s_avail
            if s_avail:
                in_stock = True

    return {
        "price": price,
        "in_stock": in_stock,
        "shoe_sizes": shoe_sizes
    }


def run_tier_b_live_parity_audit(sample_size: int = 20) -> Dict[str, Any]:
    """Query live Coach PDPs for 20 random products and verify exact 1-to-1 parity."""
    print("\n========================================================")
    print(f"Executing Phase 3 - Tier B: Live Store Parity Audit ({sample_size} Samples)")
    print("========================================================")

    files = [f for f in os.listdir(PRODUCTS_DIR) if f.endswith(".json")]
    random.seed(42)
    selected_files = random.sample(files, min(sample_size, len(files)))

    headers = get_browser_headers({"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"})
    
    audit_results = []
    passed_count = 0

    with create_http_client(custom_headers=headers, timeout_seconds=20.0) as client:
        for idx, fname in enumerate(selected_files, 1):
            fpath = os.path.join(PRODUCTS_DIR, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                stored = json.load(f)

            source_url = stored["source_url"]
            target_sku = stored["source_sku"]
            print(f"\n[{idx}/{sample_size}] Auditing: {stored['title']} ({target_sku})")
            print(f"      URL: {source_url}")

            try:
                resp = client.get(source_url)
                if resp.status_code != 200:
                    print(f"      [!] HTTP Status: {resp.status_code}")
                    audit_results.append({
                        "handle": stored["handle"],
                        "sku": target_sku,
                        "status": f"HTTP {resp.status_code}",
                        "passed": False
                    })
                    continue

                live_info = parse_live_pdp_for_sku(resp.text, target_sku)
                live_price = live_info["price"]
                stored_price = float(stored["source_price"])

                live_in_stock = live_info["in_stock"]
                stored_in_stock = stored["availability"] == "in_stock"

                is_footwear = stored.get("product_type") == "Shoes & Footwear"
                size_match = True
                if is_footwear and live_info["shoe_sizes"]:
                    for v in stored.get("variants", []):
                        m_v = re.search(r'US\s+([0-9.]+)', v.get("title", ""))
                        if m_v:
                            us_s = m_v.group(1)
                            if us_s in live_info["shoe_sizes"]:
                                expected_stock = live_info["shoe_sizes"][us_s]
                                if v.get("in_stock") != expected_stock:
                                    print(f"        [Size mismatch for US {us_s}: stored={v.get('in_stock')} vs live={expected_stock}]")
                                    size_match = False

                price_match = live_price is not None and abs(live_price - stored_price) < 0.01
                stock_match = live_in_stock == stored_in_stock
                images_valid = len(stored.get("images", [])) > 0

                item_passed = price_match and stock_match and size_match and images_valid
                if item_passed:
                    passed_count += 1
                    status_str = "PASS (100% Parity)"
                else:
                    status_str = f"MISMATCH (Price: {price_match}, Stock: {stock_match}, Sizes: {size_match})"

                print(f"      Result: {status_str} | Live Price: ${live_price} vs Stored: ${stored_price} | Live Stock: {live_in_stock} vs Stored: {stored_in_stock} | Images: {len(stored['images'])}")

                audit_results.append({
                    "sku": target_sku,
                    "title": stored["title"],
                    "product_type": stored["product_type"],
                    "stored_usd": stored_price,
                    "live_usd": live_price,
                    "stored_inr": stored["current_price"],
                    "stored_stock": stored["availability"],
                    "live_stock": "in_stock" if live_in_stock else "out_of_stock",
                    "images_count": len(stored["images"]),
                    "variants_count": len(stored["variants"]),
                    "passed": item_passed
                })

            except Exception as e:
                print(f"      [!] Parity check error: {e}")
                audit_results.append({
                    "sku": target_sku,
                    "error": str(e),
                    "passed": False
                })

            time.sleep(0.5)

    parity_score = round((passed_count / sample_size) * 100, 1)
    print(f"\n========================================================")
    print(f"[*] Tier B Parity Score: {parity_score}% ({passed_count}/{sample_size} Passed)")
    print(f"========================================================")

    out_path = "scratch/coach_audit_report.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "parity_score": parity_score,
            "passed_count": passed_count,
            "total_sampled": sample_size,
            "samples": audit_results
        }, f, indent=2)

    return {
        "parity_score": parity_score,
        "passed_count": passed_count,
        "total": sample_size,
        "results": audit_results
    }


def main():
    tier_a = run_tier_a_static_audit()
    tier_b = run_tier_b_live_parity_audit(20)

    print("\n========================================================")
    print("FINAL COACH CATALOG AUDIT SUMMARY")
    print(f"  Tier A (100% Static Check): {'PASS (100%)' if tier_a['tier_a_pass'] else 'FAIL'}")
    print(f"  Tier B (Live Store Parity): {tier_b['parity_score']}%")
    print("========================================================")


if __name__ == "__main__":
    main()
