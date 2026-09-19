"""
Production Catalog Rehydration Script: Nordstrom (On Running / Footwear)
Ingests complete multi-colorway variant matrices and accurate per-colorway pricing across all Nordstrom products.
Ensures zero dropped colorways and zero clearance price leakage (ADR 0006, ADR 0015).
Pure functions, zero classes (ADR 0004, ADR 0005).
"""
import sys
import os
import glob
import json
import time
import argparse
from typing import Dict, Any, Optional

sys.path.insert(0, os.getcwd())
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from camoufox.sync_api import Camoufox
from stores.nordstrom.camoufox_solver import solve_and_extract_pdp
from stores.nordstrom.inflow import parse_product_payload
from storage.db import save_product, build_and_save_index


def rehydrate_catalog(
    limit: Optional[int] = None,
    product_id_filter: Optional[str] = None,
    force: bool = False,
    pause_sec: float = 0.5
) -> Dict[str, Any]:
    """
    Iterate over Nordstrom products on disk, rehydrating them with full colorway matrices
    and accurate per-variant pricing via Camoufox stealth browser.
    """
    files = glob.glob("storage/db/nordstrom/products/*.json")
    print(f"[{time.strftime('%X')}] Discovered {len(files)} Nordstrom products in storage/db/nordstrom/products/")

    if product_id_filter:
        files = [f for f in files if product_id_filter in os.path.basename(f)]
        print(f"[{time.strftime('%X')}] Filtered to {len(files)} products matching '{product_id_filter}'")

    if limit and limit > 0:
        files = files[:limit]
        print(f"[{time.strftime('%X')}] Limited to {len(files)} products for this run")

    stats = {
        "total": len(files),
        "rehydrated": 0,
        "already_complete": 0,
        "delisted_404": 0,
        "failed": 0,
        "total_variants_added": 0,
        "multi_colorways_added": 0
    }

    t_start = time.time()

    print(f"[{time.strftime('%X')}] Launching Camoufox stealth browser instance...")
    with Camoufox(headless=True) as browser:
        def create_fresh_page():
            p = browser.new_page()
            def _filter(route):
                rt = route.request.resource_type
                u = route.request.url.lower()
                if rt in ["image", "media", "font"]:
                    route.abort()
                elif any(k in u for k in ["analytics", "tracking", "doubleclick", "google-analytics", "quantummetric", "branch.io", "facebook"]):
                    route.abort()
                else:
                    route.continue_()
            try:
                p.route("**/*", _filter)
            except Exception:
                pass
            return p

        page = create_fresh_page()
        page_use_count = 0

        for idx, fpath in enumerate(files, 1):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    existing_prod = json.load(f)
            except Exception as e:
                print(f"[{idx}/{len(files)}] [ERROR] Error reading {fpath}: {e}")
                stats["failed"] += 1
                continue

            p_id = existing_prod.get("id")
            handle = existing_prod.get("handle", "")
            title = existing_prod.get("title", "")
            source_url = existing_prod.get("source_url", "")
            existing_vars = existing_prod.get("variants", [])

            # Check if product has already been rehydrated (has price_range_usd)
            has_price_range = "price_range_usd" in existing_prod
            if not force and has_price_range:
                stats["already_complete"] += 1
                continue

            # Periodically rotate page to prevent Playwright DOM / memory leaks
            if page_use_count >= 5:
                try:
                    page.close()
                except Exception:
                    pass
                page = create_fresh_page()
                page_use_count = 0

            page_use_count += 1
            print(f"[{idx}/{len(files)}] Processing {p_id} | {title[:35]}... (current vars: {len(existing_vars)})")

            # Extract full PDP matrix
            t_pdp = time.time()
            solve_res = solve_and_extract_pdp(page, source_url, target_handle=handle)
            status = solve_res.get("status")
            pdp_sec = time.time() - t_pdp

            if status == "not_found":
                print(f"    [404] HTTP 404: Product delisted. Marking out of stock.")
                existing_prod["availability"] = "out_of_stock"
                existing_prod["is_active"] = False
                existing_prod["status"] = "OUT_OF_STOCK"
                for v in existing_prod.get("variants", []):
                    v["in_stock"] = False
                save_product(existing_prod)
                stats["delisted_404"] += 1
                continue

            full_matrix = solve_res.get("full_matrix")
            if not full_matrix or not full_matrix.get("colorways"):
                print(f"    [ERROR] Failed to extract full_matrix ({status}, {pdp_sec:.1f}s). Skipping.")
                stats["failed"] += 1
                try:
                    page.close()
                except Exception:
                    pass
                page = create_fresh_page()
                page_use_count = 0
                continue

            forex_rate = existing_prod.get("forex_rate_used", 95.989284)
            raw_payload = {
                "id": existing_prod["id"],
                "source_url": source_url,
                "source_sku": existing_prod.get("source_sku"),
                "title": full_matrix.get("title") or title,
                "brand": full_matrix.get("brand") or existing_prod.get("vendor"),
                "gender": full_matrix.get("gender") or existing_prod.get("specifications", {}).get("Gender"),
                "materials": full_matrix.get("materials") or existing_prod.get("material"),
                "colorways": full_matrix["colorways"],
                "created_at": existing_prod.get("created_at")
            }

            rehydrated = parse_product_payload(raw_payload, usd_to_inr_rate=forex_rate)
            if not rehydrated:
                print(f"    [ERROR] Inflow normalizer returned None for {p_id}. Skipping.")
                stats["failed"] += 1
                continue

            # Preserve existing tags, groups, and status flags
            rehydrated["tags"] = sorted(list(set(existing_prod.get("tags", []) + rehydrated.get("tags", []))))
            rehydrated["groups"] = sorted(list(set(existing_prod.get("groups", []) + ["shoes"])))
            rehydrated["status"] = "ACTIVE" if rehydrated["availability"] == "in_stock" else "OUT_OF_STOCK"
            rehydrated["is_active"] = rehydrated["availability"] == "in_stock"

            # Save atomically to disk
            save_product(rehydrated)

            c_count = len(full_matrix["colorways"])
            v_count = len(rehydrated["variants"])
            p_range = rehydrated.get("price_range_usd", {})
            print(f"    [SUCCESS] Rehydrated in {pdp_sec:.1f}s: {c_count} colorways, {v_count} variants, ${p_range.get('min')} - ${p_range.get('max')} USD")

            stats["rehydrated"] += 1
            stats["total_variants_added"] += v_count
            if c_count > 1:
                stats["multi_colorways_added"] += 1

            if pause_sec > 0:
                time.sleep(pause_sec)

            # Rebuild index every 25 products
            if stats["rehydrated"] % 25 == 0 and stats["rehydrated"] > 0:
                print(f"    [INDEX] Periodic index refresh ({stats['rehydrated']} products saved)...")
                build_and_save_index()

    total_sec = time.time() - t_start
    print(f"\n[{time.strftime('%X')}] ===================================================")
    print(f"CATALOG REHYDRATION COMPLETE in {total_sec/60:.1f} minutes")
    print(f"  Total Inspected:    {stats['total']}")
    print(f"  Rehydrated:         {stats['rehydrated']}")
    print(f"  Multi-Colorways:    {stats['multi_colorways_added']}")
    print(f"  Total Variants:     {stats['total_variants_added']}")
    print(f"  Delisted (404):     {stats['delisted_404']}")
    print(f"  Failed:             {stats['failed']}")
    print(f"===================================================\n")

    print(f"[{time.strftime('%X')}] Compiling final master index (storage/db/index.json)...")
    build_and_save_index()
    print(f"[{time.strftime('%X')}] Master index updated successfully.")

    return stats


def main():
    parser = argparse.ArgumentParser(description="Rehydrate Nordstrom product catalog with full colorways and per-variant pricing.")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of products to process")
    parser.add_argument("--product-id", type=str, default=None, help="Filter to a specific product ID")
    parser.add_argument("--force", action="store_true", help="Force rehydration even if product already has multiple colorways")
    parser.add_argument("--pause", type=float, default=0.5, help="Pause between products in seconds (default 0.5s)")

    args = parser.parse_args()
    rehydrate_catalog(
        limit=args.limit,
        product_id_filter=args.product_id,
        force=args.force,
        pause_sec=args.pause
    )


if __name__ == "__main__":
    main()
