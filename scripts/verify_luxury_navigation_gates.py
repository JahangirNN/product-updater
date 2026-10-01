"""
4-Tier Automated Verification Test Suite for Symmetrical 3-Tier Luxury Navigation
Project: The Rare Avenue (therareavenue.com)
Verifies:
  - Gate 1: Zero Men's Leakage
  - Gate 2: 100% Route Availability
  - Gate 3: Facet Interactivity & Dynamic Combinations
  - Gate 4: Live Storefront DOM Verification
"""

import sys
import os
import re
import json
import httpx

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

client = httpx.Client(timeout=25, follow_redirects=True, headers={
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
})

BASE_URL = "https://therareavenue.com"

def run_gate1():
    print("\n" + "=" * 80)
    print("GATE 1: ZERO MEN'S LEAKAGE VERIFICATION")
    print("=" * 80)

    mens_routes = [
        ("Shop All Men's Bags", f"{BASE_URL}/collections/mens-bags"),
        ("COACH Men's Collection", f"{BASE_URL}/collections/mens-bags/coach"),
        ("Michael Kors Men", f"{BASE_URL}/collections/mens-bags/michael-kors"),
        ("Messengers & Crossbody", f"{BASE_URL}/collections/mens-bags/crossbody-bags"),
        ("Billfolds & Card Cases", f"{BASE_URL}/collections/mens-bags/wallets"),
        ("Backpacks & Rucksacks", f"{BASE_URL}/collections/mens-bags/backpacks"),
        ("Briefcases & Satchels", f"{BASE_URL}/collections/mens-bags/satchels"),
    ]

    gate1_passed = True
    for title, url in mens_routes:
        resp = client.get(url)
        assert resp.status_code == 200, f"Route {url} failed with {resp.status_code}"
        
        # Extract product handles
        product_links = re.findall(r'href=[\"\']/products/([^\"\'\?]+)[\"\']', resp.text)
        unique_handles = list(dict.fromkeys(product_links))
        
        # Check for women's product contamination keywords in handles
        women_leakage = [h for h in unique_handles if any(w in h for w in ["women", "ladies", "dress", "skirt"])]
        
        print(f"[*] {title} ({url}): {len(unique_handles)} products found.")
        if women_leakage:
            print(f"  [!] LEAKAGE DETECTED in {url}: {women_leakage}")
            gate1_passed = False
        else:
            print(f"  [+] Clean: 0 women-specific handles detected.")

    # Deep verification via Shopify GraphQL that mens-bags collection has 0 Gender:Women products
    col_query = """
    query {
      collectionByHandle(handle: "mens-bags") {
        id
        title
        products(first: 100) {
          nodes {
            id
            title
            tags
          }
        }
      }
    }
    """
    data, ext, err = execute_shopify_graphql(col_query)
    if data and data.get("collectionByHandle"):
        prods = data["collectionByHandle"]["products"]["nodes"]
        leaked_nodes = []
        for p in prods:
            tags = [t.lower() for t in p["tags"]]
            if "gender:women" in tags or "women" in tags:
                leaked_nodes.append(p["title"])
        if leaked_nodes:
            print(f"  [!] GraphQL Men's collection leakage: {leaked_nodes}")
            gate1_passed = False
        else:
            print(f"  [+] GraphQL collectionByHandle(mens-bags): Verified {len(prods)} products are strictly Men's!")

    if gate1_passed:
        print("[PASSED] GATE 1: Zero Men's Leakage confirmed!")
    else:
        print("[FAILED] GATE 1 failed!")
    return gate1_passed


def run_gate2():
    print("\n" + "=" * 80)
    print("GATE 2: 100% ROUTE AVAILABILITY VERIFICATION")
    print("=" * 80)

    routes = [
        # Women
        f"{BASE_URL}/collections/womens-handbags",
        f"{BASE_URL}/collections/womens-handbags/coach",
        f"{BASE_URL}/collections/womens-handbags/jw-pei",
        f"{BASE_URL}/collections/womens-handbags/michael-kors",
        f"{BASE_URL}/collections/womens-handbags/satchels",
        f"{BASE_URL}/collections/womens-handbags/crossbody-bags",
        f"{BASE_URL}/collections/womens-handbags/totes",
        f"{BASE_URL}/collections/womens-handbags/shoulder-bags",
        f"{BASE_URL}/collections/womens-handbags/wallets",
        # Men
        f"{BASE_URL}/collections/mens-bags",
        f"{BASE_URL}/collections/mens-bags/coach",
        f"{BASE_URL}/collections/mens-bags/michael-kors",
        f"{BASE_URL}/collections/mens-bags/crossbody-bags",
        f"{BASE_URL}/collections/mens-bags/wallets",
        f"{BASE_URL}/collections/mens-bags/backpacks",
        f"{BASE_URL}/collections/mens-bags/satchels",
        # Brands
        f"{BASE_URL}/collections/coach",
        f"{BASE_URL}/collections/jw-pei",
        f"{BASE_URL}/collections/jw-pei/satchels",
        f"{BASE_URL}/collections/jw-pei/totes",
        f"{BASE_URL}/collections/michael-kors",
        f"{BASE_URL}/collections/michael-kors-watches",
        f"{BASE_URL}/collections/designer-eyewear/michael-kors",
        # Hubs
        f"{BASE_URL}/collections/designer-bags",
        f"{BASE_URL}/collections/luxury-bags",
    ]

    all_200 = True
    for r in routes:
        resp = client.get(r)
        if resp.status_code == 200:
            print(f"  [+] HTTP 200 OK: {r}")
        else:
            print(f"  [!] HTTP {resp.status_code}: {r}")
            all_200 = False

    if all_200:
        print(f"[PASSED] GATE 2: All {len(routes)} routes returned HTTP 200 OK!")
    else:
        print("[FAILED] GATE 2 failed!")
    return all_200


def run_gate3():
    print("\n" + "=" * 80)
    print("GATE 3: FACET INTERACTIVITY & DYNAMIC COMBINATIONS VERIFICATION")
    print("=" * 80)

    gate3_passed = True

    # 1. Check Category/Silhouette Accordion presence on /collections/womens-handbags
    resp1 = client.get(f"{BASE_URL}/collections/womens-handbags")
    assert resp1.status_code == 200
    has_category_acc = "Category" in resp1.text or "Silhouette" in resp1.text
    print(f"[*] /collections/womens-handbags Category accordion rendered: {has_category_acc}")
    if not has_category_acc:
        gate3_passed = False

    for sil_slug in ["satchels", "crossbody-bags", "totes", "shoulder-bags", "backpacks", "wallets"]:
        expected_url = f"/collections/womens-handbags/{sil_slug}"
        has_link = expected_url in resp1.text
        print(f"  [*] Silhouette option '{sil_slug}' link ({expected_url}): {has_link}")
        if not has_link:
            gate3_passed = False

    # 2. Check compound brand+silhouette toggling on /collections/womens-handbags/coach
    resp2 = client.get(f"{BASE_URL}/collections/womens-handbags/coach")
    assert resp2.status_code == 200
    expected_compound_satchels = "/collections/womens-handbags/coach+satchels"
    expected_compound_backpacks = "/collections/womens-handbags/backpacks+coach"
    has_satchels_link = expected_compound_satchels in resp2.text
    has_backpacks_link = expected_compound_backpacks in resp2.text
    print(f"[*] /collections/womens-handbags/coach compound link ({expected_compound_satchels}): {has_satchels_link}")
    print(f"[*] /collections/womens-handbags/coach canonical alphabetical link ({expected_compound_backpacks}): {has_backpacks_link}")
    if not has_satchels_link or not has_backpacks_link:
        gate3_passed = False

    # 3. Check active state and toggle-off on /collections/womens-handbags/coach+satchels
    resp3 = client.get(f"{BASE_URL}/collections/womens-handbags/coach+satchels")
    assert resp3.status_code == 200
    # Clicking satchels on coach+satchels should toggle back to /collections/womens-handbags/coach
    has_toggle_back_to_coach = "/collections/womens-handbags/coach" in resp3.text
    print(f"[*] /collections/womens-handbags/coach+satchels toggle-off link to /coach: {has_toggle_back_to_coach}")
    if not has_toggle_back_to_coach:
        gate3_passed = False

    # 4. Check Gender Redirection on /collections/designer-bags
    resp4 = client.get(f"{BASE_URL}/collections/designer-bags")
    assert resp4.status_code == 200
    has_all_bags_link = "/collections/designer-bags" in resp4.text
    has_men_bags_link = "/collections/mens-bags" in resp4.text
    has_women_bags_link = "/collections/womens-handbags" in resp4.text
    print(f"[*] /collections/designer-bags Gender Redirection:")
    print(f"  - All Pieces -> /collections/designer-bags: {has_all_bags_link}")
    print(f"  - Men's -> /collections/mens-bags: {has_men_bags_link}")
    print(f"  - Women's -> /collections/womens-handbags: {has_women_bags_link}")
    if not (has_all_bags_link and has_men_bags_link and has_women_bags_link):
        gate3_passed = False

    if gate3_passed:
        print("[PASSED] GATE 3: Facet Interactivity & Dynamic Combinations verified!")
    else:
        print("[FAILED] GATE 3 failed!")
    return gate3_passed


def run_gate4():
    print("\n" + "=" * 80)
    print("GATE 4: LIVE STOREFRONT DOM VERIFICATION")
    print("=" * 80)

    resp = client.get(BASE_URL)
    assert resp.status_code == 200
    html = resp.text

    gate4_passed = True

    # 1. Drawer Women links
    women_drawer_links = [
        "/collections/womens-handbags",
        "/collections/womens-handbags/coach",
        "/collections/womens-handbags/jw-pei",
        "/collections/womens-handbags/michael-kors",
        "/collections/womens-handbags/satchels",
        "/collections/womens-handbags/crossbody-bags",
        "/collections/womens-handbags/totes",
        "/collections/womens-handbags/shoulder-bags",
        "/collections/womens-handbags/wallets",
    ]
    print("[*] Verifying Women's Navigation Links in Live DOM:")
    for w in women_drawer_links:
        found = f'href="{w}"' in html or f"href='{w}'" in html
        print(f"  - {w}: {found}")
        if not found:
            gate4_passed = False

    # 2. Drawer Men links strictly to /collections/mens-bags
    men_drawer_links = [
        "/collections/mens-bags",
        "/collections/mens-bags/coach",
        "/collections/mens-bags/michael-kors",
        "/collections/mens-bags/crossbody-bags",
        "/collections/mens-bags/wallets",
        "/collections/mens-bags/backpacks",
        "/collections/mens-bags/satchels",
    ]
    print("[*] Verifying Men's Navigation Links in Live DOM:")
    for m in men_drawer_links:
        found = f'href="{m}"' in html or f"href='{m}'" in html
        print(f"  - {m}: {found}")
        if not found:
            gate4_passed = False

    # Check that old leaky query links are GONE from live header/drawer
    leaky_links = [
        "/collections/designer-bags?filter.p.tag=Men",
        "/collections/womens-handbags?filter.p.vendor=COACH",
        "/collections/womens-handbags?filter.p.vendor=MICHAEL+Michael+Kors",
        "/collections/womens-handbags?filter.p.tag=Crossbody+Bags",
    ]
    print("[*] Verifying Obsolete Leaky Query Links Are Eliminated:")
    for lk in leaky_links:
        found = lk in html
        print(f"  - {lk}: {'PRESENT [!]' if found else 'ELIMINATED [+]'}")
        if found:
            gate4_passed = False

    # 3. Brands Directory Accordions in Live DOM
    print("[*] Verifying Brands Accordion Links in Live DOM:")
    brand_links = [
        "/collections/coach",
        "/collections/womens-handbags/coach",
        "/collections/mens-bags/coach",
        "/collections/jw-pei",
        "/collections/jw-pei/satchels",
        "/collections/jw-pei/totes",
        "/collections/michael-kors",
        "/collections/womens-handbags/michael-kors",
        "/collections/michael-kors-watches",
        "/collections/designer-eyewear/michael-kors",
    ]
    for b in brand_links:
        found = f'href="{b}"' in html or f"href='{b}'" in html
        print(f"  - {b}: {found}")
        if not found:
            gate4_passed = False

    if gate4_passed:
        print("[PASSED] GATE 4: Live Storefront DOM Verification confirmed!")
    else:
        print("[FAILED] GATE 4 failed!")
    return gate4_passed


if __name__ == "__main__":
    g1 = run_gate1()
    g2 = run_gate2()
    g3 = run_gate3()
    g4 = run_gate4()

    print("\n" + "=" * 80)
    print("FINAL 4-TIER AUTOMATED VERIFICATION SUMMARY")
    print("=" * 80)
    print(f"Gate 1 (Zero Men's Leakage):          {'PASSED' if g1 else 'FAILED'}")
    print(f"Gate 2 (100% Route Availability):      {'PASSED' if g2 else 'FAILED'}")
    print(f"Gate 3 (Facet Interactivity):          {'PASSED' if g3 else 'FAILED'}")
    print(f"Gate 4 (Live Storefront DOM):          {'PASSED' if g4 else 'FAILED'}")
    print("=" * 80)

    if g1 and g2 and g3 and g4:
        print("ALL 4 GATES PASSED WITH ZERO ERRORS!")
        sys.exit(0)
    else:
        print("SOME GATES FAILED!")
        sys.exit(1)
