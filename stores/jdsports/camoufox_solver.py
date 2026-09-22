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
    if getattr(page, "_route_blocking_active", False):
        return

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
        page._route_blocking_active = True
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

        # Poll live DOM for ProductGroup / Product JSON-LD
        pg = None
        for _ in range(24):  # up to 12 seconds max wait for React hydration
            try:
                pg = page.evaluate("""() => {
                    const scripts = Array.from(document.querySelectorAll('script[type="application/ld+json"]'));
                    for (const s of scripts) {
                        try {
                            const d = JSON.parse(s.innerText || s.textContent);
                            if (d && (d['@type'] === 'ProductGroup' || d['@type'] === 'Product')) return d;
                            if (Array.isArray(d)) {
                                for (const item of d) {
                                    if (item && (item['@type'] === 'ProductGroup' || item['@type'] === 'Product')) return item;
                                }
                            }
                        } catch (e) {}
                    }
                    return null;
                }""")
            except Exception:
                pg = None

            if pg:
                break
            time.sleep(0.5)

        if not pg:
            # Fallback: check raw HTML content
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
                "error": f"ProductGroup JSON-LD not found in DOM: {page_title}"
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
