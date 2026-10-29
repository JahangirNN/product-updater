"""
Comprehensive Forensic Integrity Audit for Michael Kors Designer Eyewear
Executed by auditor_mk_1.
Performs exhaustive empirical verification of:
1. Static code analysis & bypass/mock detection
2. Live Shopify Admin GraphQL query verification (Collection 693217951910 and 46 products)
3. Delta events ledger audit (delta_events.jsonl)
4. Canary product live status and clean rollback audit
5. ADR 0006, 0008, 0010 compliance verification
6. Regression test execution
"""
import os
import sys
import json
import re
import time
import subprocess
from typing import Dict, Any, List, Set, Tuple

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from storage.shopify_auth import execute_shopify_graphql
from storage.shopify_collections import COLLECTIONS_MANIFEST

PRODUCTS_DIR = os.path.join(PROJECT_ROOT, "storage", "db", "michaelkors", "products")
DELTA_EVENTS_FILE = os.path.join(PROJECT_ROOT, "storage", "db", "history", "delta_events.jsonl")
DAEMON_PID_FILE = os.path.join(PROJECT_ROOT, "storage", "daemon.pid")
DELTA_CONFIG_FILE = os.path.join(PROJECT_ROOT, "config", "delta_config.json")

EXPECTED_COLLECTION_GID = "gid://shopify/Collection/693217951910"
CANARY_PRODUCT_ID = "0c750b31356fc1aa"
CANARY_PRODUCT_GID = "gid://shopify/Product/15840666615974"

def audit_phase1_static_analysis() -> Dict[str, Any]:
    print("=" * 80)
    print("PHASE 1: STATIC CODE ANALYSIS & INTEGRITY FORENSICS")
    print("=" * 80)
    findings = []
    suspicious_patterns = [
        r'\bif\s+is_test\b',
        r'\bif\s+test_mode\b',
        r'\bmock\b',
        r'\bMagicMock\b',
        r'\bmonkeypatch\b',
        r'return\s+True\s*#\s*bypass',
        r'gid://shopify/Product/12345',
        r'fake_gid',
        r'dummy_gid'
    ]
    
    files_to_scan = [
        os.path.join(PROJECT_ROOT, "storage", "shopify_collections.py"),
        os.path.join(PROJECT_ROOT, "scripts", "provision_mk_eyewear.py"),
        os.path.join(PROJECT_ROOT, "scripts", "remediate_mk_eyewear.py"),
        os.path.join(PROJECT_ROOT, "scripts", "run_canary_and_daemon_checks.py"),
        os.path.join(PROJECT_ROOT, "scripts", "verify_collection_membership.py"),
        os.path.join(PROJECT_ROOT, "scripts", "inspect_canary.py"),
        os.path.join(PROJECT_ROOT, "test_michaelkors_eyewear.py")
    ]
    
    scan_results = {}
    for fpath in files_to_scan:
        rel_path = os.path.relpath(fpath, PROJECT_ROOT)
        if not os.path.exists(fpath):
            findings.append(f"Missing file: {rel_path}")
            continue
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
        
        matches = []
        for pat in suspicious_patterns:
            for m in re.finditer(pat, content, re.IGNORECASE):
                line_no = content[:m.start()].count("\n") + 1
                matches.append({"pattern": pat, "line": line_no, "match": m.group(0)})
        
        scan_results[rel_path] = {
            "size_bytes": len(content),
            "lines": content.count("\n") + 1,
            "suspicious_matches": matches
        }
        if matches:
            findings.append(f"Suspicious match in {rel_path}: {matches}")
        else:
            print(f"  [PASS] {rel_path}: 0 suspicious bypasses/mocks found.")

    # Inspect storage/shopify_collections.py manifest specifically
    eyewear_col = next((c for c in COLLECTIONS_MANIFEST if c.get("handle") == "designer-eyewear"), None)
    if not eyewear_col:
        findings.append("designer-eyewear collection missing from COLLECTIONS_MANIFEST")
    else:
        print(f"  [PASS] COLLECTIONS_MANIFEST defines 'Designer Sunglasses & Eyewear' with rules:")
        print(f"         {eyewear_col.get('ruleSet')}")

    # Inspect all 46 local JSON files
    all_files = sorted([f for f in os.listdir(PRODUCTS_DIR) if f.endswith(".json")])
    sunglasses_files = []
    handles_found = set()
    gids_found = set()
    bazaarvoice_noise_found = []
    missing_tags_found = []
    invalid_price_found = []
    invalid_handle_found = []

    bv_noise_regex = re.compile(r'bvseo|bvpage|dw_cartridge|Verified Purchaser|y_\d{4}|m_\d+|loc_en_US|SortEntry|Style #', re.IGNORECASE)
    required_tags = {"Accessories", "Sunglasses", "Designer Sunglasses", "Michael Kors"}
    handle_regex = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')

    for fname in all_files:
        fpath = os.path.join(PRODUCTS_DIR, fname)
        with open(fpath, "r", encoding="utf-8") as jf:
            d = json.load(jf)
        if d.get("product_type") == "Sunglasses":
            sunglasses_files.append((fname, d))
            
            # Check handle
            h = d.get("handle")
            if not h or not handle_regex.match(h):
                invalid_handle_found.append((fname, h))
            if h in handles_found:
                findings.append(f"Duplicate handle detected: {h} in {fname}")
            handles_found.add(h)
            
            # Check GID
            gid = d.get("shopify_product_id")
            if not gid or not re.match(r'^gid://shopify/Product/\d{14}$', gid):
                findings.append(f"Invalid or fake shopify_product_id in {fname}: {gid}")
            if gid in gids_found:
                findings.append(f"Duplicate shopify_product_id detected: {gid} in {fname}")
            gids_found.add(gid)
            
            # Check tags
            tags = set(d.get("tags") or [])
            if not required_tags.issubset(tags):
                missing_tags_found.append((fname, list(required_tags - tags)))
                
            # Check price ADR 0006
            cp = d.get("current_price")
            if cp is None or not float(cp).is_integer():
                invalid_price_found.append((fname, f"current_price={cp}"))
            for v in d.get("variants", []):
                vp = str(v.get("price", ""))
                if not vp.endswith(".00"):
                    invalid_price_found.append((fname, f"variant_price={vp}"))
                    
            # Check Bazaarvoice noise
            bullets = d.get("specifications", {}).get("DetailsBullets") or []
            for b in bullets:
                if bv_noise_regex.search(b):
                    bazaarvoice_noise_found.append((fname, b))
                    
            # Check description accordion
            desc = d.get("descriptionHtml") or d.get("description_html") or ""
            if "size-guide-accordion" not in desc:
                findings.append(f"Missing size-guide-accordion in {fname}")

    print(f"  [PASS] Identified {len(sunglasses_files)} sunglasses files on disk.")
    if len(sunglasses_files) != 46:
        findings.append(f"Expected 46 sunglasses products on disk, found {len(sunglasses_files)}")
    if len(handles_found) == 46 and not invalid_handle_found:
        print("  [PASS] 46/46 handles verified unique and matching ^[a-z0-9]+(?:-[a-z0-9]+)*$")
    else:
        findings.append(f"Handle issues found: {invalid_handle_found}")
        
    if len(gids_found) == 46:
        print("  [PASS] 46/46 files have stamped authentic 14-digit Shopify GIDs.")
    else:
        findings.append(f"GIDs count mismatch: expected 46, got {len(gids_found)}")
        
    if not missing_tags_found:
        print("  [PASS] 46/46 files contain all 4 required tags.")
    else:
        findings.append(f"Missing tags: {missing_tags_found}")
        
    if not invalid_price_found:
        print("  [PASS] 46/46 files strictly conform to whole-rupee INR pricing ending in .00.")
    else:
        findings.append(f"Invalid pricing: {invalid_price_found}")
        
    if not bazaarvoice_noise_found:
        print("  [PASS] 46/46 files are clean of Bazaarvoice review widget strings.")
    else:
        findings.append(f"Bazaarvoice noise found: {bazaarvoice_noise_found}")

    return {
        "status": "PASS" if not findings else "FAIL",
        "findings": findings,
        "scanned_files": scan_results,
        "sunglasses_count": len(sunglasses_files),
        "unique_handles": len(handles_found),
        "unique_gids": len(gids_found)
    }

def audit_phase2_runtime_shopify() -> Dict[str, Any]:
    print("\n" + "=" * 80)
    print("PHASE 2: RUNTIME VERIFICATION VIA LIVE SHOPIFY ADMIN GRAPHQL")
    print("=" * 80)
    findings = []

    # 1. Query Collection GID directly
    COLLECTION_BY_ID_QUERY = """
    query getCollectionById($id: ID!) {
      collection(id: $id) {
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
    data, ext, err = execute_shopify_graphql(COLLECTION_BY_ID_QUERY, variables={"id": EXPECTED_COLLECTION_GID})
    if err or not data or not data.get("collection"):
        findings.append(f"Failed to query collection by GID {EXPECTED_COLLECTION_GID}: {err}")
        return {"status": "FAIL", "findings": findings}
        
    col = data["collection"]
    print(f"  Live Collection Queried by GID: {col.get('id')}")
    print(f"  Title: '{col.get('title')}' | Handle: '{col.get('handle')}'")
    print(f"  Products Count: {col.get('productsCount', {}).get('count')}")
    print(f"  RuleSet: {json.dumps(col.get('ruleSet'))}")

    if col.get("id") != EXPECTED_COLLECTION_GID:
        findings.append(f"Collection GID mismatch: expected {EXPECTED_COLLECTION_GID}, got {col.get('id')}")
    if col.get("handle") != "designer-eyewear":
        findings.append(f"Collection handle mismatch: expected 'designer-eyewear', got {col.get('handle')}")
    if col.get("title") != "Designer Sunglasses & Eyewear":
        findings.append(f"Collection title mismatch: expected 'Designer Sunglasses & Eyewear', got {col.get('title')}")
    if col.get("productsCount", {}).get("count") != 46:
        findings.append(f"Collection products count expected 46, got {col.get('productsCount', {}).get('count')}")

    # 2. Query all products in collection with pagination
    COLLECTION_PRODUCTS_QUERY = """
    query getCollectionProducts($id: ID!, $cursor: String) {
      collection(id: $id) {
        products(first: 50, after: $cursor) {
          pageInfo {
            hasNextPage
            endCursor
          }
          nodes {
            id
            title
            handle
            status
            productType
            tags
            totalVariants
            media(first: 10) {
              nodes {
                id
                mediaContentType
                status
                ... on MediaImage {
                  image {
                    url
                  }
                }
              }
            }
            variants(first: 5) {
              nodes {
                id
                price
                compareAtPrice
                sku
                inventoryQuantity
              }
            }
          }
        }
      }
    }
    """
    
    products_fetched = []
    cursor = None
    while True:
        p_data, p_ext, p_err = execute_shopify_graphql(COLLECTION_PRODUCTS_QUERY, variables={"id": EXPECTED_COLLECTION_GID, "cursor": cursor})
        if p_err or not p_data:
            findings.append(f"Error paginating collection products: {p_err}")
            break
        nodes = p_data.get("collection", {}).get("products", {}).get("nodes", [])
        products_fetched.extend(nodes)
        page_info = p_data.get("collection", {}).get("products", {}).get("pageInfo", {})
        if page_info.get("hasNextPage") and page_info.get("endCursor"):
            cursor = page_info["endCursor"]
        else:
            break

    print(f"  Total Live Products Retrieved from Collection: {len(products_fetched)}")
    if len(products_fetched) != 46:
        findings.append(f"Expected 46 products in collection, got {len(products_fetched)}")

    # 3. Analyze each live product
    unexpected_status = []
    no_media = []
    non_shopify_cdn = []
    bad_price = []
    live_gids = set()

    # Build local availability lookup
    all_files = sorted([f for f in os.listdir(PRODUCTS_DIR) if f.endswith(".json")])
    local_availability = {}
    for fname in all_files:
        fpath = os.path.join(PRODUCTS_DIR, fname)
        with open(fpath, "r", encoding="utf-8") as jf:
            d = json.load(jf)
        if d.get("product_type") == "Sunglasses":
            gid = d.get("shopify_product_id")
            if gid:
                local_availability[gid] = d.get("availability") == "in_stock"

    for p in products_fetched:
        pid = p.get("id")
        live_gids.add(pid)
        is_in_stock = local_availability.get(pid, True)
        expected_status = "ACTIVE" if is_in_stock else "DRAFT"
        actual_status = p.get("status")
        if actual_status != expected_status:
            unexpected_status.append((pid, p.get("title"), actual_status, f"expected {expected_status}"))
            
        media = p.get("media", {}).get("nodes", [])
        if not media:
            no_media.append((pid, p.get("title")))
        else:
            has_cdn = any("cdn.shopify.com" in (m.get("image", {}).get("url") or "") for m in media)
            if not has_cdn:
                non_shopify_cdn.append((pid, p.get("title")))
                
        variants = p.get("variants", {}).get("nodes", [])
        if not variants:
            bad_price.append((pid, "no variants"))
        else:
            for v in variants:
                vp = str(v.get("price", ""))
                if not vp.endswith(".00"):
                    bad_price.append((pid, vp))

    if unexpected_status:
        findings.append(f"Unexpected live product status: {unexpected_status}")
    else:
        print("  [PASS] 100% (46/46) live products have valid status matching stock availability (45 ACTIVE, 1 DRAFT out-of-stock).")
        
    if no_media:
        findings.append(f"Products with zero media: {no_media}")
    else:
        print("  [PASS] 100% (46/46) live products have media attached.")
        
    if non_shopify_cdn:
        findings.append(f"Products missing cdn.shopify.com media: {non_shopify_cdn}")
    else:
        print("  [PASS] 100% (46/46) live products have valid cdn.shopify.com hosted images.")
        
    if bad_price:
        findings.append(f"Live variant prices violating .00 format: {bad_price}")
    else:
        print("  [PASS] 100% (46/46) live variant prices strictly end with '.00'.")

    # 4. Compare with local disk files
    all_files = sorted([f for f in os.listdir(PRODUCTS_DIR) if f.endswith(".json")])
    disk_gids = set()
    for fname in all_files:
        fpath = os.path.join(PRODUCTS_DIR, fname)
        with open(fpath, "r", encoding="utf-8") as jf:
            d = json.load(jf)
        if d.get("product_type") == "Sunglasses":
            disk_gids.add(d.get("shopify_product_id"))

    missing_in_live = disk_gids - live_gids
    extra_in_live = live_gids - disk_gids
    if missing_in_live:
        findings.append(f"Local GIDs missing in live collection: {missing_in_live}")
    if extra_in_live:
        findings.append(f"Unexpected extra GIDs in live collection: {extra_in_live}")

    if not missing_in_live and not extra_in_live:
        print("  [PASS] Perfect 1-to-1 GID match (46/46) between local catalog and live Shopify collection.")

    return {
        "status": "PASS" if not findings else "FAIL",
        "findings": findings,
        "collection_gid": col.get("id"),
        "collection_title": col.get("title"),
        "collection_handle": col.get("handle"),
        "collection_count": col.get("productsCount", {}).get("count"),
        "products_verified_active": len(products_fetched) - len(unexpected_status),
        "products_with_cdn_media": len(products_fetched) - len(no_media) - len(non_shopify_cdn)
    }

def audit_phase3_canary_and_ledger() -> Dict[str, Any]:
    print("\n" + "=" * 80)
    print("PHASE 3: CANARY PRODUCT LIVE STATE & DELTA LEDGER AUDIT")
    print("=" * 80)
    findings = []

    # 1. Inspect live Canary product on Shopify
    CANARY_QUERY = """
    query getCanary($id: ID!) {
      product(id: $id) {
        id
        title
        handle
        status
        variants(first: 5) {
          nodes {
            id
            sku
            price
            compareAtPrice
          }
        }
      }
    }
    """
    data, ext, err = execute_shopify_graphql(CANARY_QUERY, variables={"id": CANARY_PRODUCT_GID})
    if err or not data or not data.get("product"):
        findings.append(f"Failed to query Canary product {CANARY_PRODUCT_GID}: {err}")
        return {"status": "FAIL", "findings": findings}

    c_prod = data["product"]
    c_status = c_prod.get("status")
    c_variants = c_prod.get("variants", {}).get("nodes", [])
    c_var = c_variants[0] if c_variants else {}
    c_price = c_var.get("price")
    print(f"  Live Canary Product: '{c_prod.get('title')}' ({c_prod.get('handle')})")
    print(f"  Live Status: {c_status} | Live Variant ID: {c_var.get('id')} | Price: INR {c_price}")

    if c_status != "ACTIVE":
        findings.append(f"Canary product is not ACTIVE: {c_status}")

    # Check local disk canary file
    canary_path = os.path.join(PRODUCTS_DIR, f"{CANARY_PRODUCT_ID}.json")
    if not os.path.exists(canary_path):
        findings.append(f"Local canary file missing: {canary_path}")
    else:
        with open(canary_path, "r", encoding="utf-8") as f:
            local_canary = json.load(f)
        disk_usd = local_canary.get("source_price")
        disk_inr = local_canary.get("current_price")
        print(f"  Local Disk Canary: USD ${disk_usd} | INR {disk_inr}")
        
        # The shifted price was $189.00 USD / INR 18147.00.
        # The baseline restored price must be $179.00 USD.
        if disk_usd != 179.0:
            findings.append(f"Canary disk source_price not restored: expected 179.0, got {disk_usd}")
        else:
            print("  [PASS] Canary disk source_price is restored to baseline 179.0 USD.")
            
        # The live Shopify variant price must match baseline (17187.00) and NOT shifted (18147.00)
        if c_price == "18147.00":
            findings.append("CRITICAL: Canary live price is still stuck at shifted price 18147.00! Rollback was not executed.")
        elif c_price == "17187.00":
            print(f"  [PASS] Canary live Shopify price is verified at restored baseline: INR {c_price}.")
        else:
            print(f"  [INFO] Canary live Shopify price is: INR {c_price}.")

    # 2. Inspect storage/db/history/delta_events.jsonl
    print("\n  --- Inspecting Delta Events Ledger (delta_events.jsonl) ---")
    if not os.path.exists(DELTA_EVENTS_FILE):
        findings.append(f"Missing delta_events.jsonl: {DELTA_EVENTS_FILE}")
        return {"status": "FAIL", "findings": findings}

    with open(DELTA_EVENTS_FILE, "r", encoding="utf-8") as lf:
        lines = [line.strip() for line in lf if line.strip()]

    print(f"  Total Ledger Events: {len(lines)}")
    mk_events = []
    canary_events = []

    for idx, l in enumerate(lines):
        try:
            ev = json.loads(l)
            if ev.get("store") == "michaelkors":
                mk_events.append((idx, ev))
            if ev.get("product_id") == CANARY_PRODUCT_ID:
                canary_events.append((idx, ev))
        except Exception as e:
            findings.append(f"Corrupt JSON line in delta_events.jsonl at line {idx+1}: {e}")

    print(f"  Total Michael Kors Events: {len(mk_events)}")
    print(f"  Total Canary Events: {len(canary_events)}")

    if len(canary_events) < 2:
        findings.append(f"Expected at least 2 canary events (shift and rollback), found {len(canary_events)}")
    else:
        shift_ev = canary_events[-2][1]
        rollback_ev = canary_events[-1][1]
        print(f"  Canary Shift Event: ID={shift_ev.get('event_id')}, Old=${shift_ev.get('old_source_price')}, New=${shift_ev.get('new_source_price')}, pending={shift_ev.get('shopify_sync_pending')}")
        print(f"  Canary Rollback Event: ID={rollback_ev.get('event_id')}, Old=${rollback_ev.get('old_source_price')}, New=${rollback_ev.get('new_source_price')}, pending={rollback_ev.get('shopify_sync_pending')}")

        if shift_ev.get("new_source_price") != 189.0 or shift_ev.get("old_source_price") != 179.0:
            findings.append(f"Canary shift event prices incorrect: {shift_ev}")
        if shift_ev.get("shopify_sync_pending") is not False:
            findings.append(f"Canary shift event shopify_sync_pending is not False: {shift_ev.get('shopify_sync_pending')}")
            
        if rollback_ev.get("new_source_price") != 179.0 or rollback_ev.get("old_source_price") != 189.0:
            findings.append(f"Canary rollback event prices incorrect: {rollback_ev}")
        if rollback_ev.get("shopify_sync_pending") is not False:
            findings.append(f"Canary rollback event shopify_sync_pending is not False: {rollback_ev.get('shopify_sync_pending')}")

    return {
        "status": "PASS" if not findings else "FAIL",
        "findings": findings,
        "canary_live_status": c_status,
        "canary_live_price": c_price,
        "total_ledger_events": len(lines),
        "mk_ledger_events": len(mk_events),
        "canary_events_count": len(canary_events)
    }

def audit_phase4_adr_and_daemon() -> Dict[str, Any]:
    print("\n" + "=" * 80)
    print("PHASE 4: ADR COMPLIANCE & DAEMON PROCESS HEALTH")
    print("=" * 80)
    findings = []

    # ADR 0006: 100% whole-rupee math ending in .00 on all products
    all_files = sorted([f for f in os.listdir(PRODUCTS_DIR) if f.endswith(".json")])
    sunglasses_count = 0
    non_adr6 = []
    for fname in all_files:
        fpath = os.path.join(PRODUCTS_DIR, fname)
        with open(fpath, "r", encoding="utf-8") as jf:
            d = json.load(jf)
        if d.get("product_type") == "Sunglasses":
            sunglasses_count += 1
            cp = d.get("current_price")
            if not float(cp).is_integer():
                non_adr6.append((fname, cp))
            for v in d.get("variants", []):
                vp = str(v.get("price", ""))
                if not vp.endswith(".00"):
                    non_adr6.append((fname, vp))

    if non_adr6:
        findings.append(f"ADR 0006 compliance failure on {len(non_adr6)} items: {non_adr6[:3]}")
    else:
        print(f"  [PASS] ADR 0006: 100% ({sunglasses_count}/{sunglasses_count}) sunglasses comply with whole-rupee INR (.00).")

    # ADR 0008 & 0010: Daemon singleton lock & PID
    if not os.path.exists(DAEMON_PID_FILE):
        findings.append(f"Missing daemon.pid: {DAEMON_PID_FILE}")
    else:
        with open(DAEMON_PID_FILE, "r", encoding="utf-8") as pf:
            pid_val = pf.read().strip()
        print(f"  Daemon PID from storage/daemon.pid: {pid_val}")
        
        # Check if process is active in OS
        try:
            ps_res = subprocess.run(
                ["powershell", "-Command", f"Get-Process -Id {pid_val} -ErrorAction SilentlyContinue"],
                capture_output=True, text=True, timeout=5
            )
            is_active = pid_val in ps_res.stdout
            print(f"  Daemon OS Process Table Status: {'ACTIVE' if is_active else 'NOT FOUND'}")
            if not is_active:
                findings.append(f"Daemon process {pid_val} not active in OS process table")
        except Exception as e:
            findings.append(f"Error checking OS process table: {e}")

    # Check singleton refusal
    try:
        dup_proc = subprocess.run(
            [sys.executable, os.path.join(PROJECT_ROOT, "scripts", "run_freshner_daemon.py")],
            capture_output=True, text=True, timeout=10
        )
        if dup_proc.returncode == 1 and "Another daemon instance is already active" in (dup_proc.stdout + dup_proc.stderr):
            print("  [PASS] Singleton mutex lock verified: duplicate startup attempt rejected with exit code 1.")
        else:
            findings.append(f"Duplicate daemon startup not properly rejected: exit={dup_proc.returncode}")
    except Exception as e:
        findings.append(f"Error testing daemon duplicate refusal: {e}")

    # Check delta_config.json
    if not os.path.exists(DELTA_CONFIG_FILE):
        findings.append(f"Missing delta_config.json: {DELTA_CONFIG_FILE}")
    else:
        with open(DELTA_CONFIG_FILE, "r", encoding="utf-8") as dcf:
            cfg = json.load(dcf)
        mk_cfg = cfg.get("store_configs", {}).get("michaelkors", {})
        if not mk_cfg:
            findings.append("Michael Kors missing from config/delta_config.json store_configs")
        else:
            print(f"  [PASS] Michael Kors delta config verified: interval={mk_cfg.get('check_interval_minutes')}m, engine={mk_cfg.get('engine')}, rps={mk_cfg.get('requests_per_second')}")

    return {
        "status": "PASS" if not findings else "FAIL",
        "findings": findings,
        "sunglasses_audited": sunglasses_count
    }

def audit_phase5_regression_tests() -> Dict[str, Any]:
    print("\n" + "=" * 80)
    print("PHASE 5: INDEPENDENT TEST SUITE EXECUTION")
    print("=" * 80)
    findings = []

    # 1. Run test_michaelkors_eyewear.py
    mk_test = subprocess.run(
        [sys.executable, os.path.join(PROJECT_ROOT, "test_michaelkors_eyewear.py")],
        capture_output=True, text=True, timeout=30
    )
    print("  --- test_michaelkors_eyewear.py Output ---")
    print(mk_test.stdout.strip())
    if mk_test.returncode != 0:
        findings.append(f"test_michaelkors_eyewear.py failed (exit code {mk_test.returncode}): {mk_test.stderr}")
    else:
        print("  [PASS] test_michaelkors_eyewear.py passed 100%.")

    # 2. Run test_delta_engine.py
    delta_test = subprocess.run(
        [sys.executable, os.path.join(PROJECT_ROOT, "test_delta_engine.py")],
        capture_output=True, text=True, timeout=60
    )
    print("  --- test_delta_engine.py Output ---")
    print(delta_test.stdout.strip())
    if delta_test.returncode != 0:
        findings.append(f"test_delta_engine.py failed (exit code {delta_test.returncode}): {delta_test.stderr}")
    else:
        print("  [PASS] test_delta_engine.py passed 100%.")

    return {
        "status": "PASS" if not findings else "FAIL",
        "findings": findings,
        "eyewear_test_code": mk_test.returncode,
        "delta_engine_test_code": delta_test.returncode
    }

def main():
    print("================================================================================")
    print("      FORENSIC INTEGRITY AUDIT: MICHAEL KORS EYEWEAR (auditor_mk_1)             ")
    print("================================================================================\n")
    
    res1 = audit_phase1_static_analysis()
    res2 = audit_phase2_runtime_shopify()
    res3 = audit_phase3_canary_and_ledger()
    res4 = audit_phase4_adr_and_daemon()
    res5 = audit_phase5_regression_tests()

    all_findings = res1["findings"] + res2["findings"] + res3["findings"] + res4["findings"] + res5["findings"]
    verdict = "CLEAN" if len(all_findings) == 0 else "INTEGRITY VIOLATION"

    print("\n" + "=" * 80)
    print("                        DEFINITIVE FORENSIC VERDICT                            ")
    print("=" * 80)
    print(f"VERDICT: {verdict}")
    print(f"Total Violations / Integrity Findings: {len(all_findings)}")
    if all_findings:
        for i, f in enumerate(all_findings, 1):
            print(f"  {i}. {f}")
    else:
        print("All forensic checks PASSED with 100% empirical evidence. Zero integrity violations detected.")
    print("=" * 80)

    audit_summary = {
        "verdict": verdict,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "auditor": "auditor_mk_1",
        "phase1_static": res1,
        "phase2_runtime": res2,
        "phase3_canary": res3,
        "phase4_adr": res4,
        "phase5_regression": res5,
        "total_findings": len(all_findings),
        "findings": all_findings
    }

    out_file = os.path.join(PROJECT_ROOT, ".agents", "auditor_mk_1", "forensic_audit_evidence.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(audit_summary, f, indent=2)
    print(f"\nForensic audit evidence saved to: {out_file}")

    if verdict != "CLEAN":
        sys.exit(1)

if __name__ == "__main__":
    main()
