"""
Camoufox Stealth Solver for JD Sports (Pure Functions, ADR 0005, ADR 0010)
Bypasses Akamai Bot Manager and extracts live price and stock availability locally (zero API tokens).
"""
import time
import json
import re
from typing import Dict, Any, Optional
from camoufox.sync_api import Camoufox


def create_jdsports_browser(headless: bool = True):
    """Instantiate a Camoufox stealth browser instance for JD Sports."""
    return Camoufox(headless=headless)


def setup_camoufox_route_blocking(page: Any) -> None:
    """
    Attach route filter to Camoufox page to block images, media, fonts,
    and third-party trackers, keeping only primary scripts and documents needed for Akamai + React.
    """
    def _route_filter(route):
        rt = route.request.resource_type
        u = route.request.url.lower()
        if rt in ["image", "media", "font"]:
            route.abort()
        elif any(k in u for k in ["analytics", "tracking", "doubleclick", "google-analytics", "quantummetric", "branch.io", "facebook", "criteo", "hotjar"]):
            route.abort()
        else:
            route.continue_()

    try:
        page.route("**/*", _route_filter)
    except Exception:
        pass


def solve_and_extract_pdp(page: Any, url: str, target_handle: str = "") -> Dict[str, Any]:
    """
    Navigate to a JD Sports PDP via Camoufox, handle Akamai challenge, and extract price & variant stock from JSON-LD.
    """
    t_start = time.perf_counter()
    try:
        setup_camoufox_route_blocking(page)
        resp = page.goto(url, wait_until="domcontentloaded", timeout=45000)
        status_code = resp.status if resp else 0

        if status_code == 404:
            elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)
            return {
                "status": "not_found",
                "price_usd": 0.0,
                "availability": "out_of_stock",
                "variants": [],
                "elapsed_ms": elapsed_ms,
                "message": "Product delisted (HTTP 404)"
            }

        # Wait for React/Next.js hydration and ProductGroup JSON-LD injection
        html = page.content()
        for _ in range(24):
            if "ProductGroup" in html or ("hasVariant" in html and "@type" in html):
                break
            time.sleep(0.5)
            html = page.content()

        if "Access Denied" in html:
            elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)
            return {
                "status": "rate_limited",
                "price_usd": 0.0,
                "availability": "unknown",
                "variants": [],
                "elapsed_ms": elapsed_ms,
                "error": "Akamai Access Denied"
            }

        # Extract JSON-LD scripts
        scripts = re.findall(r'<script[^>]*type=[\'"]application/ld\+json[\'"][^>]*>(.*?)</script>', html, re.DOTALL | re.IGNORECASE)
        pg = None
        for s in scripts:
            try:
                data = json.loads(s.strip())
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("@type") in ("ProductGroup", "Product"):
                            pg = item
                            break
                elif isinstance(data, dict):
                    if data.get("@type") in ("ProductGroup", "Product"):
                        pg = data
                        break
                if pg:
                    break
            except Exception:
                continue

        if not pg:
            page_title = page.title()
            if "out of stock" in html.lower() or "sold out" in html.lower():
                return {
                    "status": "success",
                    "price_usd": 0.0,
                    "availability": "out_of_stock",
                    "variants": [],
                    "elapsed_ms": round((time.perf_counter() - t_start) * 1000, 2)
                }
            return {
                "status": "error",
                "price_usd": 0.0,
                "availability": "unknown",
                "variants": [],
                "elapsed_ms": round((time.perf_counter() - t_start) * 1000, 2),
                "error": f"ProductGroup JSON-LD not found: {page_title}"
            }

        raw_variants = pg.get("hasVariant") or []
        if pg.get("@type") == "Product":
            raw_variants = [pg]

        extracted_variants = []
        lowest_price = 0.0
        for v in raw_variants:
            v_sku = str(v.get("sku") or "").strip()
            v_size = str(v.get("size") or "").strip()
            v_offers = v.get("offers") or {}
            if isinstance(v_offers, list) and v_offers:
                v_offers = v_offers[0]

            v_price = 0.0
            v_in_stock = False
            if isinstance(v_offers, dict):
                try:
                    v_price = float(v_offers.get("price") or 0.0)
                except (ValueError, TypeError):
                    v_price = 0.0
                avail_str = str(v_offers.get("availability") or "").lower()
                v_in_stock = ("instock" in avail_str or "in_stock" in avail_str)

            if v_price > 0 and (lowest_price == 0.0 or v_price < lowest_price):
                lowest_price = v_price

            extracted_variants.append({
                "sku": v_sku,
                "size": v_size,
                "available": v_in_stock,
                "price_usd": v_price
            })

        has_any_stock = any(v["available"] for v in extracted_variants)
        overall_avail = "in_stock" if has_any_stock else "out_of_stock"

        elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)
        return {
            "status": "success",
            "price_usd": lowest_price,
            "availability": overall_avail,
            "variants": extracted_variants,
            "elapsed_ms": elapsed_ms
        }

    except Exception as err:
        elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)
        return {
            "status": "error",
            "price_usd": 0.0,
            "availability": "unknown",
            "variants": [],
            "elapsed_ms": elapsed_ms,
            "error": str(err)
        }
