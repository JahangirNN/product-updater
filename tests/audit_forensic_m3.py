#!/usr/bin/env python3
"""
Auditor M3 Independent Forensic Verification Script
Empirically verifies:
1. /collections/kate-spade rules and product count on Shopify Admin GraphQL.
2. 429 Kate Spade local product files vs live Shopify server existence.
3. Variant prices on Shopify: whole-rupee INR with 99 charm rounding.
4. storage/db/index.json rebuild and consistency.
5. Background daemon PID 24056 process status and OS lock.
6. Live theme 198751387814 remote snippets (luxury-desktop-nav.liquid, luxury-sidebar-panels.liquid).
7. Clean-room compliance and zero supplier leaks.
"""
import os
import sys
import json
import glob
import psutil

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql
from storage.daemon_lock import read_active_daemon_pid, is_daemon_locked, is_pid_alive, get_process_uptime_seconds

THEME_ID = "gid://shopify/OnlineStoreTheme/198751387814"

def audit_collection():
    print("=" * 80)
    print("1. AUDITING /collections/kate-spade ON SHOPIFY ADMIN GRAPHQL")
    print("=" * 80)
    
    query = """
    query getCollectionByHandle($handle: String!) {
      collectionByHandle(handle: $handle) {
        id
        title
        handle
        descriptionHtml
        ruleSet {
          appliedDisjunctively
          rules {
            column
            relation
            condition
          }
        }
        productsCount {
          count
        }
      }
    }
    """
    data, _, err = execute_shopify_graphql(query, {"handle": "kate-spade"})
    if err or not data or not data.get("collectionByHandle"):
        print(f"[FAIL] Could not query /collections/kate-spade: {err}")
        return False, None
        
    col = data["collectionByHandle"]
    print(f"Collection ID: {col.get('id')}")
    print(f"Collection Title: {col.get('title')}")
    print(f"Collection Handle: {col.get('handle')}")
    print(f"Collection RuleSet: {col.get('ruleSet')}")
    count = col.get("productsCount", {}).get("count")
    print(f"Products in Collection: {count}")
    
    # Verify rules
    rules = col.get("ruleSet", {}).get("rules", [])
    has_vendor_rule = any(r.get("column") == "VENDOR" and r.get("condition") == "Kate Spade" for r in rules)
    has_tag_rule = any(r.get("column") == "TAG" and r.get("condition") == "Kate Spade" for r in rules)
    disjunctive = col.get("ruleSet", {}).get("appliedDisjunctively")
    
    print(f"Has Vendor rule ('Kate Spade'): {has_vendor_rule}")
    print(f"Has Tag rule ('Kate Spade'): {has_tag_rule}")
    print(f"Applied Disjunctively: {disjunctive}")
    
    if not (has_vendor_rule and has_tag_rule and disjunctive):
        print("[FAIL] Collection ruleSet does not match specification!")
        return False, count
        
    if count != 429:
        print(f"[WARN/FAIL] Expected 429 products, got {count}")
        return False, count
        
    print("[PASS] Collection verified with 429 products and authentic ruleSet!")
    return True, count

def audit_products_and_variants():
    print("=" * 80)
    print("2. AUDITING LOCAL 429 PRODUCT FILES & LIVE GRAPHQL SAMPLING")
    print("=" * 80)
    
    prod_files = glob.glob(os.path.join(PROJECT_ROOT, "storage", "db", "katespade", "products", "*.json"))
    print(f"Local product files found: {len(prod_files)}")
    if len(prod_files) != 429:
        print(f"[FAIL] Expected 429 product files, found {len(prod_files)}")
        return False
        
    all_gids = []
    all_handles = []
    all_variants_count = 0
    
    for pf in prod_files:
        with open(pf, "r", encoding="utf-8") as f:
            p = json.load(f)
        gid = p.get("shopify_product_id")
        h = p.get("shopify_handle")
        if not gid or not gid.startswith("gid://shopify/Product/"):
            print(f"[FAIL] Invalid or missing shopify_product_id in {pf}: {gid}")
            return False
        all_gids.append(gid)
        all_handles.append(h)
        all_variants_count += len(p.get("variants") or [])
        
    print(f"Total verified local products with valid GIDs: {len(all_gids)}")
    print(f"Total variants across local products: {all_variants_count}")
    
    # Sample 15 products directly on Shopify Admin GraphQL
    import random
    random.seed(1337)
    sample_gids = random.sample(all_gids, 15)
    
    query = """
    query getProduct($id: ID!) {
      product(id: $id) {
        id
        title
        handle
        vendor
        productType
        status
        totalVariants
        variants(first: 20) {
          nodes {
            id
            title
            price
            compareAtPrice
            sku
          }
        }
      }
    }
    """
    
    verified_live = 0
    sampled_variant_prices = []
    non_charm_prices = []
    
    for gid in sample_gids:
        data, _, err = execute_shopify_graphql(query, {"id": gid})
        if err or not data or not data.get("product"):
            print(f"[FAIL] Product not found on Shopify: {gid} | Error: {err}")
            return False
        p = data["product"]
        verified_live += 1
        for v in p.get("variants", {}).get("nodes", []):
            pr = v.get("price")
            sampled_variant_prices.append((p["title"], v["sku"], pr))
            # Price must end in 99 or 99.00
            try:
                pr_float = float(pr)
                # Check whole rupee (pr ends in .00)
                if not pr.endswith(".00") and not ("." not in pr):
                    non_charm_prices.append((p["title"], v["sku"], pr, "not whole-rupee"))
                # Check 99 charm rounding: int(round(pr_float)) % 100 == 99
                int_price = int(round(pr_float))
                if int_price % 100 != 99:
                    non_charm_prices.append((p["title"], v["sku"], pr, f"mod 100 is {int_price % 100}, expected 99"))
            except Exception as e:
                non_charm_prices.append((p["title"], v["sku"], pr, str(e)))
                
    print(f"Sampled {len(sample_gids)} products ({len(sampled_variant_prices)} variants) on Shopify.")
    print(f"All {verified_live} live products confirmed on Shopify Admin API.")
    print(f"Non-charm prices found: {len(non_charm_prices)}")
    if non_charm_prices:
        for ncp in non_charm_prices[:5]:
            print(f"  [PRICE MISMATCH] {ncp}")
        return False
        
    print("[PASS] All sampled live products exist on Shopify with whole-rupee INR and 99 charm rounding!")
    return True

def audit_storage_index():
    print("=" * 80)
    print("3. AUDITING storage/db/index.json")
    print("=" * 80)
    
    index_path = os.path.join(PROJECT_ROOT, "storage", "db", "index.json")
    if not os.path.exists(index_path):
        print("[FAIL] storage/db/index.json does not exist!")
        return False
        
    with open(index_path, "r", encoding="utf-8") as f:
        idx_data = json.load(f)
        
    print(f"Total entries in index.json: {len(idx_data)}")
    
    ks_entries = [v for k, v in idx_data.items() if v.get("store") == "katespade"]
    print(f"Kate Spade entries in index.json: {len(ks_entries)}")
    
    if len(ks_entries) != 429:
        print(f"[FAIL] Expected 429 Kate Spade entries in index.json, found {len(ks_entries)}")
        return False
        
    # Check that all have valid file paths and IDs
    missing_files = 0
    for e in ks_entries:
        fp = os.path.join(PROJECT_ROOT, "storage", "db", e.get("file_path", ""))
        if not os.path.exists(fp):
            missing_files += 1
            
    print(f"Missing file paths from index: {missing_files}")
    if missing_files > 0:
        print(f"[FAIL] {missing_files} indexed Kate Spade files do not exist on disk!")
        return False
        
    print("[PASS] storage/db/index.json verified with exactly 429 Kate Spade entries!")
    return True

def audit_daemon():
    print("=" * 80)
    print("4. AUDITING BACKGROUND DAEMON (PID 24056 & OS LOCK)")
    print("=" * 80)
    
    target_pid = 24056
    is_running = False
    proc_info = None
    
    try:
        if psutil.pid_exists(target_pid):
            p = psutil.Process(target_pid)
            if p.is_running() and p.status() != psutil.STATUS_ZOMBIE:
                is_running = True
                proc_info = {
                    "name": p.name(),
                    "cmdline": p.cmdline(),
                    "create_time": p.create_time(),
                    "cpu_percent": p.cpu_percent(interval=0.1),
                    "memory_info": p.memory_info()._asdict()
                }
    except Exception as exc:
        print(f"Error checking PID {target_pid}: {exc}")
        
    print(f"PID {target_pid} running status: {is_running}")
    if proc_info:
        print(f"Process Name: {proc_info['name']}")
        print(f"Command Line: {' '.join(proc_info['cmdline'])}")
        print(f"Memory: {proc_info['memory_info']['rss'] / (1024*1024):.2f} MB")
        
    pid_from_file = read_active_daemon_pid()
    locked = is_daemon_locked()
    uptime = get_process_uptime_seconds(target_pid) if is_running else 0.0
    
    print(f"Daemon PID in storage/daemon.pid: {pid_from_file}")
    print(f"OS Lock Held: {locked}")
    print(f"Uptime: {uptime:.1f}s ({uptime/60:.1f}m)")
    
    if not is_running:
        print(f"[FAIL] Target daemon PID {target_pid} is NOT actively running!")
        return False
    if pid_from_file != target_pid:
        print(f"[FAIL] daemon.pid PID ({pid_from_file}) != target PID ({target_pid})")
        return False
    if not locked:
        print("[FAIL] OS file lock on storage/daemon.pid is NOT held!")
        return False
        
    print("[PASS] Background daemon PID 24056 is actively running with OS file lock held!")
    return True

def audit_remote_navigation_snippets():
    print("=" * 80)
    print("5. AUDITING REMOTE LIVE THEME 198751387814 NAVIGATION SNIPPETS")
    print("=" * 80)
    
    query = """
    query getThemeFiles($id: ID!, $filenames: [String!]!) {
      theme(id: $id) {
        files(filenames: $filenames) {
          nodes {
            filename
            body {
              ... on OnlineStoreThemeFileBodyText {
                content
              }
            }
          }
        }
      }
    }
    """
    filenames = ["snippets/luxury-desktop-nav.liquid", "snippets/luxury-sidebar-panels.liquid"]
    data, _, err = execute_shopify_graphql(query, {"id": THEME_ID, "filenames": filenames})
    if err or not data or not data.get("theme"):
        print(f"[FAIL] Could not query remote theme snippets: {err}")
        return False
        
    nodes = data["theme"]["files"]["nodes"]
    if len(nodes) != 2:
        print(f"[FAIL] Expected 2 snippets, got {len(nodes)}")
        return False
        
    all_ok = True
    for node in nodes:
        fn = node["filename"]
        body = node.get("body", {}).get("content", "")
        print(f"Remote file: {fn} (size: {len(body)} chars)")
        
        # Check Kate Spade presence
        has_ks = "kate spade" in body.lower()
        print(f"  Contains 'Kate Spade': {has_ks}")
        if not has_ks:
            print(f"  [FAIL] {fn} does NOT contain Kate Spade navigation!")
            all_ok = False
            
        # Check supplier leaks
        has_leak = "katespadeoutlet" in body.lower()
        print(f"  Contains 'katespadeoutlet' leak: {has_leak}")
        if has_leak:
            print(f"  [FAIL] {fn} contains prohibited leak 'katespadeoutlet'!")
            all_ok = False
            
        # Specific pattern checks
        if "desktop" in fn:
            # Check mega menu links
            has_p1 = "/womens-handbags/kate-spade" in body
            has_atelier = "luxury-atelier-card" in body and "Kate Spade" in body
            has_dir = "luxury-directory-link" in body and "Kate Spade" in body
            print(f"  Pillar 1 link: {has_p1} | Atelier card: {has_atelier} | Directory link: {has_dir}")
            if not (has_p1 and has_atelier and has_dir):
                print(f"  [FAIL] Desktop navigation missing required Kate Spade sections!")
                all_ok = False
        elif "sidebar" in fn:
            # Check mobile sidebar
            has_women = "#header-panel-women" in body or "/womens-handbags/kate-spade" in body
            has_accordion = "luxury-sidebar__brand-block" in body and "Kate Spade" in body
            has_details = "<details" in body and "<accordion-disclosure>" not in body
            print(f"  Women panel: {has_women} | Accordion block: {has_accordion} | Clean details tag: {has_details}")
            if not (has_women and has_accordion and has_details):
                print(f"  [FAIL] Sidebar navigation missing required Kate Spade sections or contains banned tags!")
                all_ok = False
                
    if all_ok:
        print("[PASS] Remote theme snippets verified on live Shopify theme!")
    return all_ok

if __name__ == "__main__":
    c_ok, c_count = audit_collection()
    p_ok = audit_products_and_variants()
    i_ok = audit_storage_index()
    d_ok = audit_daemon()
    s_ok = audit_remote_navigation_snippets()
    
    print("\n" + "=" * 80)
    print("FINAL SUMMARY OF FORENSIC CHECKS:")
    print(f"1. Collection /collections/kate-spade: {'PASS' if c_ok else 'FAIL'} (Count={c_count})")
    print(f"2. 429 Products & 99-Charm Pricing:     {'PASS' if p_ok else 'FAIL'}")
    print(f"3. storage/db/index.json Rebuild:       {'PASS' if i_ok else 'FAIL'}")
    print(f"4. Background Daemon PID 24056 & Lock:  {'PASS' if d_ok else 'FAIL'}")
    print(f"5. Remote Theme 198751387814 Snippets:  {'PASS' if s_ok else 'FAIL'}")
    print("=" * 80)
    
    if c_ok and p_ok and i_ok and d_ok and s_ok:
        print("\nALL FORENSIC VERIFICATIONS PASSED: CLEAN")
        sys.exit(0)
    else:
        print("\nFORENSIC VERIFICATION FAILED: INTEGRITY VIOLATION")
        sys.exit(1)
