"""
Shopify Product Readiness & Validation Module
Enforces Tier 1, Tier 2, and Tier 3 validation rules according to SHOPIFY_INTEGRATION_SPEC.md.
Pure functions, zero classes (ADR 0005).
"""
from typing import Any, Dict, List, Tuple


def validate_product(product: Dict[str, Any]) -> Tuple[bool, str, List[str]]:
    """
    Validate a canonical product dictionary against Shopify requirements.
    
    Returns:
        (is_valid_for_api, suggested_status, warnings)
        suggested_status is one of: 'ACTIVE', 'DRAFT', 'ARCHIVED'
    """
    warnings: List[str] = []
    hard_failures: List[str] = []

    # 1. Tier 1: Mandatory Requirements
    title = str(product.get("title", "")).strip()
    if not title:
        hard_failures.append("TIER_1_ERROR: Missing product title")
    elif len(title) > 255:
        hard_failures.append("TIER_1_ERROR: Product title exceeds 255 characters")

    variants = product.get("variants", [])
    if not variants or not isinstance(variants, list):
        hard_failures.append("TIER_1_ERROR: Product must have at least 1 variant")
    else:
        for idx, var in enumerate(variants):
            price = var.get("price")
            if price is None or float(price) <= 0:
                hard_failures.append(f"TIER_1_ERROR: Variant #{idx+1} has invalid or zero price")

    if hard_failures:
        return False, "DRAFT", hard_failures + warnings

    # 2. Tier 2: Critical E-Commerce Checks
    images = product.get("images", [])
    if not images:
        warnings.append("WARNING_NO_IMAGES: Product has zero photos")

    vendor = str(product.get("vendor", "")).strip()
    if not vendor:
        warnings.append("WARNING_NO_VENDOR: Product vendor/brand is blank")

    for idx, var in enumerate(variants):
        sku = str(var.get("sku", "")).strip()
        if not sku:
            warnings.append(f"WARNING_NO_SKU: Variant #{idx+1} missing SKU")
        
        price = float(var.get("price", 0))
        compare_at = var.get("compare_at_price")
        if compare_at is not None:
            compare_val = float(compare_at)
            if compare_val > 0 and compare_val < price:
                warnings.append(f"WARNING_INVALID_MSRP: Compare price ({compare_val}) is lower than sale price ({price})")

    # 3. Tier 3: Enrichment Quality Checks
    desc = str(product.get("descriptionHtml", "")).strip()
    if not desc:
        warnings.append("WARNING_NO_DESCRIPTION: Empty body description")

    specs = product.get("specifications", {})
    if not specs:
        warnings.append("WARNING_NO_SPECIFICATIONS: Missing product specs")

    material = product.get("material") or specs.get("material") or specs.get("Major Material")
    if not material:
        warnings.append("WARNING_NO_MATERIAL: Missing fabric/material details")

    # 4. Determine Shopify Status
    # Status is ACTIVE only if in stock, has images, and zero critical warnings
    is_in_stock = product.get("availability") == "in_stock"
    has_critical_warning = any(w.startswith("WARNING_NO_IMAGES") or w.startswith("WARNING_NO_SKU") for w in warnings)

    if is_in_stock and images and not has_critical_warning:
        status = "ACTIVE"
    else:
        status = "DRAFT"

    return True, status, warnings
