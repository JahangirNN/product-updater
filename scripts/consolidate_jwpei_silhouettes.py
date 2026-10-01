"""
Phase 2: JW PEI Canonical Silhouette Consolidation
===================================================
Collapses 491 split-colorway Shopify products (one per color) into one
canonical product per silhouette family (grouped by product_type SKU).

Strategy per family:
  1. Pick the "canonical" product (most variants / highest variant count).
  2. Merge all unique variants from sibling products (dedup by SKU).
  3. Update the canonical Shopify product with all merged variants via productSet.
  4. Unpublish (draft) all sibling duplicate products on Shopify.
  5. Write canonical_product_id back to every sibling's local JSON.

Run:
    python scripts/consolidate_jwpei_silhouettes.py [--dry-run] [--family 2T68]
"""
import argparse
import json
import os
import sys
import time
import collections
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from storage.shopify_auth import execute_shopify_graphql
from storage.shopify_taxonomy import prepare_product_set_payload
import storage.logger as _logger
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("consolidate_jwpei")

DB_PATH = ROOT / "storage" / "db" / "jwpei" / "products"

# ---------------------------------------------------------------------------
# GraphQL helpers
# ---------------------------------------------------------------------------

PRODUCT_UPDATE_STATUS = """
mutation productUpdate($input: ProductInput!) {
  productUpdate(input: $input) {
    product { id status }
    userErrors { field message }
  }
}
"""

PRODUCT_SET_MUT = """
mutation productSet($input: ProductSetInput!, $synchronous: Boolean!) {
  productSet(input: $input, synchronous: $synchronous) {
    product {
      id
      handle
      title
      variants(first: 100) {
        nodes { id title sku price }
      }
    }
    userErrors { field message code }
  }
}
"""


def load_all_products():
    products = []
    for f in DB_PATH.iterdir():
        if not f.suffix == ".json":
            continue
        try:
            with open(f, encoding="utf-8") as fh:
                p = json.load(fh)
            p["_local_file"] = str(f)
            products.append(p)
        except Exception as e:
            log.warning("Skip %s: %s", f.name, e)
    return products


def group_by_family(products):
    """Group products by product_type (the SKU family code)."""
    families = collections.defaultdict(list)
    for p in products:
        pt = p.get("product_type", "").strip()
        if pt:
            families[pt].append(p)
    return families


def pick_canonical(family_products):
    """Choose the product with the most variants as the canonical master."""
    return max(family_products, key=lambda p: len(p.get("variants", [])))


def merge_variants(family_products):
    """
    Merge all variants from all sibling products, deduped by SKU.
    Returns a list of unique variant dicts.
    """
    seen_skus = {}
    for p in family_products:
        for v in p.get("variants", []):
            sku = v.get("sku", "")
            if sku and sku not in seen_skus:
                seen_skus[sku] = v
            elif not sku:
                # No SKU — use title as fallback key
                key = v.get("title", "") + "|" + str(v.get("price", ""))
                if key not in seen_skus:
                    seen_skus[key] = v
    return list(seen_skus.values())


def build_canonical_product(canonical, merged_variants):
    """Return a copy of canonical with the merged variant list."""
    merged = dict(canonical)
    merged["variants"] = merged_variants
    # Make sure title doesn't have ' - COLOR' suffix for the canonical
    title = merged.get("title", "")
    if " - " in title:
        merged["title"] = title.rsplit(" - ", 1)[0].strip()
    return merged


def unpublish_product(shopify_id, dry_run):
    """Set product status to DRAFT on Shopify."""
    if dry_run:
        log.info("[DRY-RUN] Would unpublish %s", shopify_id)
        return True
    data, _ext, err = execute_shopify_graphql(PRODUCT_UPDATE_STATUS, {
        "input": {"id": shopify_id, "status": "DRAFT"}
    })
    if err:
        log.error("Unpublish HTTP error for %s: %s", shopify_id, err)
        return False
    errors = (data or {}).get("productUpdate", {}).get("userErrors", [])
    if errors:
        log.error("Unpublish userErrors for %s: %s", shopify_id, errors)
        return False
    log.info("Unpublished (drafted) %s", shopify_id)
    return True


def update_canonical_on_shopify(canonical_product, dry_run):
    """Push merged canonical product to Shopify via productSet."""
    try:
        payload = prepare_product_set_payload(canonical_product)
    except Exception as e:
        log.error("Failed to build payload for %s: %s", canonical_product.get("title"), e)
        return None

    if dry_run:
        n_variants = len(payload.get("variants", []))
        log.info("[DRY-RUN] Would push canonical '%s' with %d variants", payload.get("title"), n_variants)
        return "DRY-RUN-ID"

    data, _ext, err = execute_shopify_graphql(PRODUCT_SET_MUT, {
        "input": payload,
        "synchronous": True,
    })
    if err:
        log.error("productSet HTTP error for '%s': %s", canonical_product.get("title"), err)
        return None
    ps = (data or {}).get("productSet", {})
    errors = ps.get("userErrors", [])
    if errors:
        log.error("productSet userErrors for '%s': %s", canonical_product.get("title"), errors)
        return None
    product = ps.get("product", {})
    shopify_id = product.get("id")
    log.info("Updated canonical '%s' -> %s (%d variants)",
             product.get("title"), shopify_id,
             len(product.get("variants", {}).get("nodes", [])))
    return shopify_id



def save_local(path, product_data):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(product_data, fh, ensure_ascii=False, indent=2)


def process_family(family_name, family_products, dry_run):
    log.info("=" * 60)
    log.info("Family: %s  (%d products)", family_name, len(family_products))

    if len(family_products) == 1:
        log.info("  Single product — nothing to consolidate, skip.")
        return {"family": family_name, "skipped": True}

    canonical = pick_canonical(family_products)
    merged_variants = merge_variants(family_products)
    log.info("  Canonical: '%s' (%s)", canonical.get("title"), canonical.get("shopify_product_id"))
    log.info("  Siblings: %d | Merged variants: %d", len(family_products) - 1, len(merged_variants))

    canonical_copy = build_canonical_product(canonical, merged_variants)

    # 1. Update canonical on Shopify
    shopify_id = update_canonical_on_shopify(canonical_copy, dry_run)
    if not shopify_id:
        return {"family": family_name, "error": "productSet failed"}

    # 2. Update canonical local file
    if not dry_run:
        canonical_copy["shopify_product_id"] = shopify_id
        canonical_copy["canonical"] = True
        save_local(canonical["_local_file"], canonical_copy)

    # 3. Unpublish siblings
    unpublished = []
    failed = []
    for sibling in family_products:
        if sibling["_local_file"] == canonical["_local_file"]:
            continue
        sid = sibling.get("shopify_product_id")
        if sid:
            ok = unpublish_product(sid, dry_run)
            if ok:
                unpublished.append(sid)
                # Mark local file as archived
                if not dry_run:
                    sibling_copy = dict(sibling)
                    sibling_copy["archived"] = True
                    sibling_copy["canonical_product_id"] = shopify_id
                    save_local(sibling["_local_file"], sibling_copy)
            else:
                failed.append(sid)
        # Rate-limit
        time.sleep(0.3)

    log.info("  Unpublished %d siblings, %d failed", len(unpublished), len(failed))
    return {
        "family": family_name,
        "canonical_shopify_id": shopify_id,
        "canonical_title": canonical_copy.get("title"),
        "total_variants": len(merged_variants),
        "siblings_unpublished": len(unpublished),
        "siblings_failed": failed,
    }


def main():
    parser = argparse.ArgumentParser(description="Consolidate JW PEI silhouettes")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    parser.add_argument("--family", help="Process only this product_type family (e.g. 2T68)")
    args = parser.parse_args()

    log.info("Loading JW PEI catalog...")
    products = load_all_products()
    log.info("Total products loaded: %d", len(products))

    families = group_by_family(products)
    log.info("Total silhouette families: %d", len(families))

    # Show summary
    multi = {k: v for k, v in families.items() if len(v) > 1}
    single = {k: v for k, v in families.items() if len(v) == 1}
    log.info("Families with duplicates (need consolidation): %d", len(multi))
    log.info("Families with single product (skip): %d", len(single))
    log.info("")

    if args.dry_run:
        log.info("*** DRY-RUN MODE — no changes will be written ***")
        log.info("")

    # Filter to specific family if requested
    target_families = {args.family: families[args.family]} if args.family and args.family in families else multi

    results = []
    for family_name, family_products in sorted(target_families.items(), key=lambda x: -len(x[1])):
        try:
            result = process_family(family_name, family_products, args.dry_run)
            results.append(result)
        except Exception as e:
            log.error("Error processing family %s: %s", family_name, e, exc_info=True)
            results.append({"family": family_name, "error": str(e)})
        time.sleep(0.5)

    log.info("")
    log.info("=" * 60)
    log.info("CONSOLIDATION SUMMARY")
    log.info("=" * 60)
    success = [r for r in results if "canonical_shopify_id" in r]
    skipped = [r for r in results if r.get("skipped")]
    errors = [r for r in results if "error" in r]
    log.info("Consolidated: %d families", len(success))
    log.info("Skipped (single): %d families", len(skipped))
    log.info("Errors: %d families", len(errors))
    total_unpublished = sum(r.get("siblings_unpublished", 0) for r in success)
    log.info("Total sibling products unpublished: %d", total_unpublished)
    if errors:
        log.warning("Failed families: %s", [e["family"] for e in errors])

    # Write results JSON
    out_path = ROOT / "logs" / "consolidation_results.json"
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)
    log.info("Results written to %s", out_path)


if __name__ == "__main__":
    main()
