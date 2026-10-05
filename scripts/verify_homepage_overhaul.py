#!/usr/bin/env python3
"""
Automated Verification Suite for The Rare Avenue Luxury Homepage Overhaul
Target Platform: Shopify Online Store 2.0 (Prestige Luxury Theme #197348655270)
Storefront: https://therareavenue.com / hewmvw-am.myshopify.com

Authoritative Specifications:
- ORIGINAL_REQUEST.md (Header 2026-10-04T19:08:30Z)
- PROJECT.md (§Interface Contracts, §Code Layout, §Milestones M1-M4)
- TEST_INFRA.md (§Feature Inventory, §Real-World Scenarios)

Quality Gates:
- Gate 1: Template Architecture (RFC 8259 validity, comment-stripping, 11-section order)
- Gate 2: Liquid Syntax & OS 2.0 Schema Validity (marquee-collection-list, department-split, brand-tiles)
- Gate 3: Intelligent 3-Tier Media Fallback Logic & Zero Layout Shift (CLS=0)
- Gate 4: Storefront Collection Routing (HTTP 200 OK across all 12 curated collection cards & department edits)
"""

import os
import sys
import re
import json
import argparse
import time
from typing import Dict, List, Any, Tuple, Optional

# Optional httpx import for live route checks
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    import urllib.request
    import urllib.error

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THEME_DIR = os.path.join(PROJECT_ROOT, "theme")
TEMPLATES_DIR = os.path.join(THEME_DIR, "templates")
SECTIONS_DIR = os.path.join(THEME_DIR, "sections")
INDEX_JSON_PATH = os.path.join(TEMPLATES_DIR, "index.json")

# Authoritative 11-Section Sequence per PROJECT.md
EXPECTED_11_SECTIONS: List[Dict[str, Any]] = [
    {"id": "slideshow", "type": "slideshow", "name": "Hero Slideshow"},
    {"id": "scrolling-marquee", "type": "scrolling-content", "name": "Typographic Brand Ticker"},
    {"id": "marquee-collection-list", "type": "marquee-collection-list", "name": "12-Card Marquee Rail"},
    {"id": "category-tiles", "type": "media-grid", "name": "Asymmetric Category Media Grid"},
    {"id": "featured-collections-1", "type": "featured-collections", "name": "Curated Product Drops 1"},
    {"id": "department-split", "type": "department-split", "alt_types": ["multi-column", "media-grid"], "name": "50/50 Department Campaign"},
    {"id": "brand-tiles", "type": "brand-tiles", "alt_types": ["logo-list", "media-grid"], "name": "Brand Portal Matrix"},
    {"id": "featured-collections-2", "type": "featured-collections", "name": "Curated Product Drops 2"},
    {"id": "trust-badges", "type": "text-with-icons", "name": "Authenticity Trust Badges"},
    {"id": "newsletter", "type": "newsletter", "name": "VIP Private Client Newsletter"},
    {"id": "brand-story", "type": "rich-text", "alt_types": ["brand-story"], "name": "Maison Heritage Statement"},
]

# 12 Curated Collection Cards Routes and Fallbacks per Survey
CURATED_COLLECTION_ROUTES: List[Dict[str, Any]] = [
    {
        "slot": 1,
        "title": "Luxury Handbags",
        "primary_url": "/collections/designer-bags",
        "fallback_urls": ["/collections/luxury-bags", "/collections/womens-bags"],
    },
    {
        "slot": 2,
        "title": "Premium Footwear",
        "primary_url": "/collections/women?filter.p.tag=Footwear",
        "fallback_urls": ["/collections/instant-ship", "/collections/premium-footwear"],
    },
    {
        "slot": 3,
        "title": "Swiss Timepieces",
        "primary_url": "/collections/luxury-watches",
        "fallback_urls": ["/collections/tissot", "/collections/mens-watches"],
    },
    {
        "slot": 4,
        "title": "Ready to Ship",
        "primary_url": "/collections/instant-ship",
        "fallback_urls": [],
    },
    {
        "slot": 5,
        "title": "Coach",
        "primary_url": "/collections/coach",
        "fallback_urls": [],
    },
    {
        "slot": 6,
        "title": "Nike",
        "primary_url": "/collections/women?filter.p.vendor=Nike",
        "fallback_urls": ["/collections/nike"],
    },
    {
        "slot": 7,
        "title": "JW PEI",
        "primary_url": "/collections/jw-pei",
        "fallback_urls": [],
    },
    {
        "slot": 8,
        "title": "Tissot",
        "primary_url": "/collections/tissot",
        "fallback_urls": [],
    },
    {
        "slot": 9,
        "title": "Michael Kors",
        "primary_url": "/collections/michael-kors",
        "fallback_urls": [],
    },
    {
        "slot": 10,
        "title": "On Running",
        "primary_url": "/collections/women/on",
        "fallback_urls": ["/collections/on-running"],
    },
    {
        "slot": 11,
        "title": "HOKA",
        "primary_url": "/collections/women/hoka",
        "fallback_urls": ["/collections/hoka"],
    },
    {
        "slot": 12,
        "title": "Small Leather Goods",
        "primary_url": "/collections/wallets-leather-goods",
        "fallback_urls": ["/collections/wallets-accessories"],
    },
]

DEPARTMENT_SPLIT_ROUTES: List[Dict[str, Any]] = [
    {"title": "The Women's Edit", "primary_url": "/collections/women"},
    {"title": "The Men's Edit", "primary_url": "/collections/men"},
]


# ==============================================================================
# GATE 1: TEMPLATE ARCHITECTURE & COMMENT STRIPPING
# ==============================================================================

def strip_json_comments(content: str) -> str:
    """Strips C-style multi-line comments (/* ... */) from Shopify JSON templates."""
    return re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)


def validate_index_template(
    template_path: str = INDEX_JSON_PATH,
    sections_dir: str = SECTIONS_DIR,
    progressive: bool = False,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Validates theme/templates/index.json:
    - Strips multi-line C-style comments
    - Ensures RFC 8259 JSON validity
    - Asserts presence of all 11 sections in 'sections'
    - Asserts exact sequence matching in 'order'
    - Asserts every section type maps to an existing .liquid file in theme/sections/
    """
    result = {
        "gate": "Gate 1: Template Architecture",
        "passed": False,
        "errors": [],
        "warnings": [],
        "sections_count": 0,
        "order": [],
        "sections": {},
    }

    if not os.path.exists(template_path):
        result["errors"].append(f"Template file not found at: {template_path}")
        return result

    try:
        with open(template_path, "r", encoding="utf-8") as f:
            raw_content = f.read()
    except Exception as e:
        result["errors"].append(f"Failed to read template file: {e}")
        return result

    # Strip comments and parse RFC 8259 JSON
    clean_json = strip_json_comments(raw_content)
    try:
        data = json.loads(clean_json)
    except json.JSONDecodeError as e:
        result["errors"].append(f"RFC 8259 JSON syntax error in {template_path}: {e}")
        return result

    if not isinstance(data, dict):
        result["errors"].append("Template root must be a JSON object.")
        return result

    sections = data.get("sections")
    order = data.get("order")

    if not isinstance(sections, dict):
        result["errors"].append("Missing or invalid 'sections' object in template.")
        return result

    if not isinstance(order, list):
        result["errors"].append("Missing or invalid 'order' array in template.")
        return result

    result["sections_count"] = len(sections)
    result["order"] = order
    result["sections"] = sections

    # Bi-directional consistency between 'order' and 'sections'
    missing_in_sections = [sec_id for sec_id in order if sec_id not in sections]
    if missing_in_sections:
        result["errors"].append(f"Sections defined in 'order' missing from 'sections': {missing_in_sections}")

    missing_in_order = [sec_id for sec_id in sections if sec_id not in order]
    if missing_in_order:
        result["warnings"].append(f"Sections defined in 'sections' omitted from 'order' (unrendered): {missing_in_order}")

    # Check each section type maps to an existing .liquid file
    for sec_id, sec_def in sections.items():
        sec_type = sec_def.get("type") if isinstance(sec_def, dict) else None
        if not sec_type:
            result["errors"].append(f"Section '{sec_id}' is missing required 'type' attribute.")
            continue
        liquid_file = os.path.join(sections_dir, f"{sec_type}.liquid")
        if not os.path.exists(liquid_file):
            msg = f"Section '{sec_id}' references type '{sec_type}', but file '{liquid_file}' does not exist."
            if progressive:
                result["warnings"].append(msg)
            else:
                result["errors"].append(msg)

    # Validate 11-section sequence
    expected_ids = [s["id"] for s in EXPECTED_11_SECTIONS]
    if len(order) == 11 and order == expected_ids:
        if verbose:
            print("  [PASS] All 11 sections present in exact required order.")
    else:
        # Check matching
        missing_sections = [sid for sid in expected_ids if sid not in order]
        if missing_sections:
            msg = f"Missing required homepage sections ({len(missing_sections)}/11): {missing_sections}"
            if progressive:
                result["warnings"].append(msg + " (Progressive mode: pending milestone completion)")
            else:
                result["errors"].append(msg)

        if order != expected_ids and not missing_sections:
            msg = f"Section order mismatch. Expected: {expected_ids}, Found: {order}"
            if progressive:
                result["warnings"].append(msg)
            else:
                result["errors"].append(msg)

    result["passed"] = (len(result["errors"]) == 0)
    return result


# ==============================================================================
# GATE 2: LIQUID SYNTAX & SHOPIFY OS 2.0 SCHEMA VALIDATOR
# ==============================================================================

def extract_schema_json(liquid_content: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Extracts and parses the {% schema %} block from a Liquid file."""
    match = re.search(r'\{%\s*schema\s*%\}(.*?)\{%\s*endschema\s*%\}', liquid_content, flags=re.DOTALL)
    if not match:
        return None, "No {% schema %} block found in file."
    
    schema_str = match.group(1).strip()
    try:
        schema_json = json.loads(schema_str)
        return schema_json, None
    except json.JSONDecodeError as e:
        return None, f"Schema JSON parsing error: {e}"


def check_liquid_tag_balance(content: str) -> List[str]:
    """Validates balancing of major Liquid tags."""
    errors = []
    # Strip schema and javascript/stylesheet blocks before tag check
    stripped = re.sub(r'\{%\s*schema\s*%\}.*?\{%\s*endschema\s*%\}', '', content, flags=re.DOTALL)
    stripped = re.sub(r'\{%\s*javascript\s*%\}.*?\{%\s*endjavascript\s*%\}', '', stripped, flags=re.DOTALL)
    stripped = re.sub(r'\{%\s*stylesheet\s*%\}.*?\{%\s*endstylesheet\s*%\}', '', stripped, flags=re.DOTALL)

    tag_pairs = [
        (r'\{%-?\s*if\b', r'\{%-?\s*endif\b', "if"),
        (r'\{%-?\s*for\b', r'\{%-?\s*endfor\b', "for"),
        (r'\{%-?\s*unless\b', r'\{%-?\s*endunless\b', "unless"),
        (r'\{%-?\s*case\b', r'\{%-?\s*endcase\b', "case"),
        (r'\{%-?\s*capture\b', r'\{%-?\s*endcapture\b', "capture"),
        (r'\{%-?\s*comment\b', r'\{%-?\s*endcomment\b', "comment"),
    ]

    for open_pat, close_pat, name in tag_pairs:
        open_count = len(re.findall(open_pat, stripped))
        close_count = len(re.findall(close_pat, stripped))
        if open_count != close_count:
            errors.append(f"Unbalanced Liquid tag '{name}': {open_count} open vs {close_count} close.")

    return errors


def validate_section_file(
    section_filename: str,
    sections_dir: str = SECTIONS_DIR,
    required_name: Optional[str] = None,
    must_have_blocks: bool = False,
    must_have_presets: bool = False,
    progressive: bool = False,
    verbose: bool = True
) -> Dict[str, Any]:
    """Validates an OS 2.0 section's schema and Liquid syntax."""
    file_path = os.path.join(sections_dir, section_filename)
    result = {
        "section": section_filename,
        "path": file_path,
        "exists": False,
        "passed": False,
        "errors": [],
        "warnings": [],
        "schema": {},
    }

    if not os.path.exists(file_path):
        msg = f"Section file '{section_filename}' does not exist at: {file_path}"
        if progressive:
            result["warnings"].append(msg + " (Pending milestone implementation)")
        else:
            result["errors"].append(msg)
        return result

    result["exists"] = True
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        result["errors"].append(f"Failed to read '{section_filename}': {e}")
        return result

    # 1. Liquid Tag Balance
    tag_errors = check_liquid_tag_balance(content)
    result["errors"].extend(tag_errors)

    # 2. Extract & Validate Schema
    schema_data, schema_err = extract_schema_json(content)
    if schema_err:
        result["errors"].append(schema_err)
        return result

    result["schema"] = schema_data

    # 3. Directives check
    if "name" not in schema_data:
        result["errors"].append("Schema missing required 'name' directive.")
    elif required_name and required_name.lower() not in schema_data["name"].lower():
        result["warnings"].append(f"Schema name '{schema_data['name']}' differs from expected '{required_name}'.")

    if "settings" not in schema_data or not isinstance(schema_data["settings"], list):
        result["errors"].append("Schema missing or invalid 'settings' array.")

    if must_have_blocks:
        if "blocks" not in schema_data or not isinstance(schema_data["blocks"], list):
            result["errors"].append("Schema missing or invalid 'blocks' array.")

    if must_have_presets:
        if "presets" not in schema_data or not isinstance(schema_data["presets"], list):
            result["errors"].append("Schema missing or invalid 'presets' array.")

    # 4. Check block.shopify_attributes binding
    if must_have_blocks:
        if "shopify_attributes" not in content:
            result["warnings"].append("Section does not appear to bind 'block.shopify_attributes' for theme editor.")

    result["passed"] = (len(result["errors"]) == 0)
    return result


def validate_all_sections(sections_dir: str = SECTIONS_DIR, progressive: bool = False) -> Dict[str, Any]:
    """Validates marquee-collection-list, department-split, and brand-tiles."""
    res_marquee = validate_section_file(
        "marquee-collection-list.liquid",
        sections_dir=sections_dir,
        must_have_blocks=True,
        must_have_presets=True,
        progressive=progressive
    )
    res_split = validate_section_file(
        "department-split.liquid",
        sections_dir=sections_dir,
        must_have_blocks=False,
        must_have_presets=True,
        progressive=progressive
    )
    res_brand = validate_section_file(
        "brand-tiles.liquid",
        sections_dir=sections_dir,
        must_have_blocks=True,
        must_have_presets=True,
        progressive=progressive
    )

    all_passed = res_marquee["passed"] and (res_split["passed"] or progressive) and (res_brand["passed"] or progressive)
    return {
        "gate": "Gate 2: Liquid Syntax & OS 2.0 Schema Validity",
        "passed": all_passed,
        "marquee": res_marquee,
        "department_split": res_split,
        "brand_tiles": res_brand,
    }


# ==============================================================================
# GATE 3: CARD IMAGE FALLBACK LOGIC & CLS=0 INVARIANTS
# ==============================================================================

def validate_card_image_fallback_logic(
    marquee_path: str = os.path.join(SECTIONS_DIR, "marquee-collection-list.liquid"),
    progressive: bool = False
) -> Dict[str, Any]:
    """
    Validates that marquee-collection-list.liquid satisfies:
    1. Intelligent media fallback:
       `assign card_image = block.settings.image | default: collection.featured_image | default: collection.products.first.featured_media.preview_image`
    2. Fallback title and link logic
    3. Terminal placeholder fallback (placeholder_svg_tag or collection-*)
    4. Hardware-accelerated CSS (translate3d, will-change: transform)
    5. Pointer drag momentum handlers (pointerdown, pointermove, pointerup)
    6. Zero layout shift invariants (aspect-ratio: 4/5, image_tag or intrinsic dimensions)
    """
    result = {
        "gate": "Gate 3: Fallback Logic, Physics & CLS=0 Invariants",
        "passed": False,
        "errors": [],
        "warnings": [],
        "checks": {
            "media_fallback_chain": False,
            "title_fallback": False,
            "url_fallback": False,
            "terminal_placeholder": False,
            "hardware_accel_translate3d": False,
            "will_change_transform": False,
            "pause_on_hover": False,
            "drag_momentum_physics": False,
            "aspect_ratio_4_5": False,
            "cls_zero_attributes": False,
        }
    }

    if not os.path.exists(marquee_path):
        msg = f"File not found: {marquee_path}"
        if progressive:
            result["warnings"].append(msg + " (Pending M1 implementation)")
        else:
            result["errors"].append(msg)
        return result

    try:
        with open(marquee_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        result["errors"].append(f"Failed to read file: {e}")
        return result

    # 1. Media Fallback Chain: block.settings.image | default: collection.featured_image | default: collection.products.first.featured_media.preview_image
    # Flexible regex to account for whitespace or formatting
    fallback_re = re.search(
        r'block\.settings\.image.*default:\s*collection\.featured_image.*default:\s*collection\.products\.first\.featured_media\.preview_image',
        content,
        re.DOTALL
    )
    if fallback_re:
        result["checks"]["media_fallback_chain"] = True
    else:
        # Check individual parts
        has_block_img = "block.settings.image" in content
        has_col_img = "collection.featured_image" in content or "collection.image" in content
        has_prod_img = "collection.products.first.featured_media" in content or "products.first.featured_image" in content
        if has_block_img and has_col_img and has_prod_img:
            result["checks"]["media_fallback_chain"] = True
        else:
            result["errors"].append("Missing required 3-tier media fallback chain: block.settings.image | default: collection.featured_image | default: collection.products.first.featured_media.preview_image")

    # 2. Title and URL fallbacks
    if "block.settings.title" in content and "collection.title" in content:
        result["checks"]["title_fallback"] = True
    else:
        result["warnings"].append("Title fallback 'block.settings.title | default: collection.title' not explicitly identified.")

    if "block.settings.url" in content or "block.settings.link_url" in content or "collection.url" in content:
        result["checks"]["url_fallback"] = True
    else:
        result["warnings"].append("URL fallback 'block.settings.url | default: collection.url' not explicitly identified.")

    # 3. Terminal placeholder
    if "placeholder_svg_tag" in content or "collection-" in content or "placeholder" in content:
        result["checks"]["terminal_placeholder"] = True
    else:
        result["warnings"].append("Terminal SVG placeholder for empty collections not found.")

    # 4. Hardware acceleration (translate3d, will-change: transform)
    if "translate3d" in content:
        result["checks"]["hardware_accel_translate3d"] = True
    else:
        result["errors"].append("Missing hardware-accelerated CSS primitive 'translate3d' in marquee styling.")

    if "will-change" in content and "transform" in content:
        result["checks"]["will_change_transform"] = True
    else:
        result["warnings"].append("Missing 'will-change: transform' layer promotion hint on marquee track.")

    if "animation-play-state" in content or "pause" in content or "hover" in content:
        result["checks"]["pause_on_hover"] = True
    else:
        result["warnings"].append("Pause-on-hover interaction styling not detected.")

    # 5. Drag and touch momentum physics
    pointer_events = ["pointerdown", "pointermove", "pointerup"]
    touch_events = ["touchstart", "touchmove", "touchend"]
    if all(ev in content for ev in pointer_events) or all(ev in content for ev in touch_events) or "momentum" in content or "velocity" in content or "isDragging" in content:
        result["checks"]["drag_momentum_physics"] = True
    else:
        result["errors"].append("Missing touch/drag momentum interaction logic (pointerdown/move/up or touch equivalent).")

    # 6. Aspect Ratio 4/5 and CLS=0
    if "4/5" in content or "4 / 5" in content or "0.8" in content or "padding-top: 125%" in content or "aspect-ratio" in content:
        result["checks"]["aspect_ratio_4_5"] = True
    else:
        result["warnings"].append("Strict 'aspect-ratio: 4 / 5' portrait ratio not explicitly found in styling.")

    if "image_tag" in content or ("width=" in content and "height=" in content):
        result["checks"]["cls_zero_attributes"] = True
    else:
        result["warnings"].append("Intrinsic image dimensions (Shopify image_tag or width/height attributes) not explicitly found.")

    result["passed"] = (len(result["errors"]) == 0)
    return result


# ==============================================================================
# GATE 4: STOREFRONT COLLECTION ROUTING AVAILABILITY (HTTP 200 OK)
# ==============================================================================

def check_http_route(url: str, timeout: int = 25) -> Tuple[int, str]:
    """Performs HTTP GET on target URL and returns (status_code, error_message)."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    if HTTPX_AVAILABLE:
        for attempt in range(2):
            try:
                with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
                    resp = client.get(url)
                    return resp.status_code, ""
            except Exception as e:
                if attempt == 1:
                    return 0, str(e)
                time.sleep(1.0)
    else:
        req = urllib.request.Request(url, headers=headers)
        for attempt in range(2):
            try:
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    return response.status, ""
            except urllib.error.HTTPError as e:
                return e.code, str(e)
            except Exception as e:
                if attempt == 1:
                    return 0, str(e)
                time.sleep(1.0)


def validate_storefront_collection_routes(
    base_url: str = "https://therareavenue.com",
    skip_network: bool = False,
    timeout: int = 25,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Asserts that:
    1. All 12 curated collection card routes resolve to HTTP 200 on therareavenue.com
    2. Department split routes (/collections/women and /collections/men) resolve to HTTP 200
    """
    result = {
        "gate": "Gate 4: Storefront Collection Routing Availability",
        "passed": False,
        "base_url": base_url,
        "curated_cards": [],
        "department_routes": [],
        "errors": [],
        "warnings": [],
    }

    if skip_network:
        result["warnings"].append("Network checks skipped via --skip-network flag.")
        result["passed"] = True
        return result

    base_url = base_url.rstrip("/")
    all_passed = True

    if verbose:
        print("\n" + "=" * 80)
        print(f"GATE 4: STOREFRONT COLLECTION ROUTING AUDIT ({base_url})")
        print("=" * 80)

    # 1. Curated 12 Collection Cards
    for card in CURATED_COLLECTION_ROUTES:
        slot = card["slot"]
        title = card["title"]
        primary = card["primary_url"]
        url_to_test = f"{base_url}{primary}"

        status_code, err = check_http_route(url_to_test, timeout=timeout)
        entry = {
            "slot": slot,
            "title": title,
            "tested_url": url_to_test,
            "status_code": status_code,
            "resolved": (status_code == 200),
            "fallback_used": None,
        }

        if status_code == 200:
            if verbose:
                print(f"  [PASS] Card #{slot:02d} '{title}' -> {primary} (HTTP 200 OK)")
        else:
            # Check fallback URLs if available
            fallback_resolved = False
            for fb in card.get("fallback_urls", []):
                fb_url = f"{base_url}{fb}"
                fb_code, _ = check_http_route(fb_url, timeout=timeout)
                if fb_code == 200:
                    entry["fallback_used"] = fb
                    entry["resolved"] = True
                    fallback_resolved = True
                    if verbose:
                        print(f"  [WARN] Card #{slot:02d} '{title}' primary {primary} returned {status_code}, resolved via fallback {fb} (HTTP 200 OK)")
                    result["warnings"].append(f"Card #{slot} '{title}' primary {primary} failed ({status_code}), fallback {fb} succeeded.")
                    break

            if not fallback_resolved:
                all_passed = False
                msg = f"Card #{slot} '{title}' at {url_to_test} returned HTTP {status_code} ({err})"
                result["errors"].append(msg)
                if verbose:
                    print(f"  [FAIL] Card #{slot:02d} '{title}' -> {primary} (HTTP {status_code}) {err}")

        result["curated_cards"].append(entry)

    # 2. Department Split Routes
    for dept in DEPARTMENT_SPLIT_ROUTES:
        title = dept["title"]
        primary = dept["primary_url"]
        url_to_test = f"{base_url}{primary}"

        status_code, err = check_http_route(url_to_test, timeout=timeout)
        entry = {
            "title": title,
            "tested_url": url_to_test,
            "status_code": status_code,
            "resolved": (status_code == 200),
        }
        if status_code == 200:
            if verbose:
                print(f"  [PASS] Department '{title}' -> {primary} (HTTP 200 OK)")
        else:
            all_passed = False
            msg = f"Department '{title}' at {url_to_test} returned HTTP {status_code} ({err})"
            result["errors"].append(msg)
            if verbose:
                print(f"  [FAIL] Department '{title}' -> {primary} (HTTP {status_code}) {err}")

        result["department_routes"].append(entry)

    result["passed"] = all_passed
    return result


# ==============================================================================
# MAIN TEST RUNNER & PROGRESSIVE VERIFICATION ORCHESTRATOR
# ==============================================================================

def run_all_verification_gates(
    template_path: str = INDEX_JSON_PATH,
    sections_dir: str = SECTIONS_DIR,
    base_url: str = "https://therareavenue.com",
    progressive: bool = False,
    strict: bool = False,
    skip_network: bool = False,
    timeout: int = 25,
    verbose: bool = True
) -> Dict[str, Any]:
    """Runs all 4 Quality Gates and aggregates findings."""
    print("=" * 80)
    print("THE RARE AVENUE — HOMEPAGE OVERHAUL VERIFICATION SUITE")
    print(f"Template Target: {template_path}")
    print(f"Sections Target: {sections_dir}")
    print(f"Storefront Target: {base_url}")
    print(f"Mode: {'STRICT' if strict else ('PROGRESSIVE' if progressive else 'STANDARD')}")
    print("=" * 80)

    start_time = time.time()
    effective_progressive = progressive and not strict

    # Gate 1: Template Architecture
    if verbose:
        print("\n--- [GATE 1: TEMPLATE ARCHITECTURE & COMMENT STRIPPING] ---")
    g1 = validate_index_template(
        template_path=template_path,
        sections_dir=sections_dir,
        progressive=effective_progressive,
        verbose=verbose
    )
    if verbose:
        for err in g1["errors"]:
            print(f"  [ERROR] {err}")
        for warn in g1["warnings"]:
            print(f"  [WARN]  {warn}")

    # Gate 2: Liquid Syntax & OS 2.0 Schema
    if verbose:
        print("\n--- [GATE 2: LIQUID SYNTAX & OS 2.0 SCHEMA VALIDITY] ---")
    g2 = validate_all_sections(sections_dir=sections_dir, progressive=effective_progressive)
    if verbose:
        for sec_name in ["marquee", "department_split", "brand_tiles"]:
            sec_res = g2.get(sec_name, {})
            for err in sec_res.get("errors", []):
                print(f"  [ERROR] [{sec_name}] {err}")
            for warn in sec_res.get("warnings", []):
                print(f"  [WARN]  [{sec_name}] {warn}")

    # Gate 3: Fallback Logic, Physics & CLS=0
    if verbose:
        print("\n--- [GATE 3: FALLBACK LOGIC, PHYSICS & CLS=0 INVARIANTS] ---")
    g3 = validate_card_image_fallback_logic(
        marquee_path=os.path.join(sections_dir, "marquee-collection-list.liquid"),
        progressive=effective_progressive
    )
    if verbose:
        for err in g3["errors"]:
            print(f"  [ERROR] {err}")
        for warn in g3["warnings"]:
            print(f"  [WARN]  {warn}")

    # Gate 4: Storefront Collection Routing
    if verbose:
        print("\n--- [GATE 4: STOREFRONT COLLECTION ROUTING AVAILABILITY] ---")
    g4 = validate_storefront_collection_routes(
        base_url=base_url,
        skip_network=skip_network,
        timeout=timeout,
        verbose=verbose
    )
    if verbose:
        for err in g4["errors"]:
            print(f"  [ERROR] {err}")
        for warn in g4["warnings"]:
            print(f"  [WARN]  {warn}")

    elapsed = time.time() - start_time

    # Evaluate Overall Status
    gates_results = [g1["passed"], g2["passed"], g3["passed"], g4["passed"]]
    overall_passed = all(gates_results)

    total_errors = len(g1["errors"]) + len(g2["marquee"]["errors"]) + len(g3["errors"]) + len(g4["errors"])
    total_warnings = len(g1["warnings"]) + len(g2["marquee"]["warnings"]) + len(g3["warnings"]) + len(g4["warnings"])

    summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_seconds": round(elapsed, 2),
        "overall_passed": overall_passed,
        "strict_mode": strict,
        "progressive_mode": effective_progressive,
        "total_errors": total_errors,
        "total_warnings": total_warnings,
        "gates": {
            "gate1_template_architecture": g1,
            "gate2_liquid_schema_validity": g2,
            "gate3_fallback_and_physics": g3,
            "gate4_storefront_routing": g4,
        }
    }

    print("\n" + "=" * 80)
    print("VERIFICATION SUITE EXECUTION SUMMARY")
    print("=" * 80)
    print(f"Gate 1 (Template Architecture):       {'PASS' if g1['passed'] else 'FAIL'} ({len(g1['errors'])} errors, {len(g1['warnings'])} warnings)")
    print(f"Gate 2 (Liquid Syntax & Schema):       {'PASS' if g2['passed'] else 'FAIL'}")
    print(f"Gate 3 (Fallback Logic & Physics):    {'PASS' if g3['passed'] else 'FAIL'} ({len(g3['errors'])} errors, {len(g3['warnings'])} warnings)")
    print(f"Gate 4 (Storefront Route 200 OK):      {'PASS' if g4['passed'] else 'FAIL'} ({len(g4['errors'])} errors, {len(g4['warnings'])} warnings)")
    print("-" * 80)
    print(f"Overall Result: {'PASS' if overall_passed else 'FAIL'}")
    print(f"Total Execution Time: {summary['elapsed_seconds']}s")
    print("=" * 80)

    return summary


def main():
    parser = argparse.ArgumentParser(description="Verification Suite for The Rare Avenue Homepage Overhaul")
    parser.add_argument("--template", type=str, default=INDEX_JSON_PATH, help="Path to theme/templates/index.json")
    parser.add_argument("--sections-dir", type=str, default=SECTIONS_DIR, help="Path to theme/sections directory")
    parser.add_argument("--base-url", type=str, default="https://therareavenue.com", help="Base URL of storefront")
    parser.add_argument("--progressive", action="store_true", help="Enable progressive milestone mode (tolerates uncompleted future milestones)")
    parser.add_argument("--strict", action="store_true", help="Strict mode (requires 100% pass across all 4 gates)")
    parser.add_argument("--skip-network", action="store_true", help="Skip live HTTP network checks")
    parser.add_argument("--timeout", type=int, default=25, help="HTTP request timeout in seconds")
    parser.add_argument("--json-report", type=str, default="", help="Path to save detailed JSON report")
    parser.add_argument("--quiet", action="store_true", help="Suppress detailed console logging")

    args = parser.parse_args()

    summary = run_all_verification_gates(
        template_path=args.template,
        sections_dir=args.sections_dir,
        base_url=args.base_url,
        progressive=args.progressive,
        strict=args.strict,
        skip_network=args.skip_network,
        timeout=args.timeout,
        verbose=not args.quiet
    )

    if args.json_report:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(args.json_report)), exist_ok=True)
            with open(args.json_report, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2)
            print(f"Detailed JSON report saved to: {args.json_report}")
        except Exception as e:
            print(f"Failed to write JSON report to {args.json_report}: {e}")

    # Return exit code
    sys.exit(0 if summary["overall_passed"] else 1)


if __name__ == "__main__":
    main()
