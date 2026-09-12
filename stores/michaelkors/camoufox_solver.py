"""
Camoufox Stealth Solver for Michael Kors (Pure Functions, ADR 0005, ADR 0010)
Bypasses Akamai Bot Manager and extracts live price and stock availability.
"""
import time
import re
from typing import Dict, Any, Optional
from camoufox.sync_api import Camoufox


def create_michaelkors_browser(headless: bool = True):
    """Instantiate a Camoufox stealth browser instance for Michael Kors."""
    return Camoufox(headless=headless)


def solve_and_extract_pdp(page, url: str, target_handle: str = "") -> Dict[str, Any]:
    """
    Navigate to a Michael Kors PDP via Camoufox, handle Akamai, and extract price & availability.
    Prefers native SFCC variation AJAX when SKU is detectable, otherwise anchors price under product header.
    """
    t_start = time.perf_counter()
    try:
        # Check if SKU can be extracted to use SFCC AJAX directly
        m_sku = re.search(r'/([A-Z0-9\-]+)\.html', url)
        if m_sku:
            sku = m_sku.group(1)
            sfcc_url = f"https://www.michaelkors.com/on/demandware.store/Sites-mk_us-Site/en_US/Product-Variation?pid={sku}&format=ajax"
            page.goto(sfcc_url, wait_until="domcontentloaded", timeout=15000)
            text = page.evaluate("() => document.body.innerText")
            if "product" in text:
                import json
                d = json.loads(text)
                p = d.get("product", {})
                price_obj = p.get("price") or {}
                sales_obj = price_obj.get("sales") if isinstance(price_obj, dict) else None
                list_obj = price_obj.get("list") if isinstance(price_obj, dict) else None
                p_usd = 0.0
                if isinstance(sales_obj, dict) and sales_obj.get("value"):
                    p_usd = float(sales_obj["value"])
                elif isinstance(list_obj, dict) and list_obj.get("value"):
                    p_usd = float(list_obj["value"])

                is_avail = bool(p.get("available", False))
                is_ready = bool(p.get("readyToOrder", False))
                avail_status = "in_stock" if (is_avail and is_ready) else ("in_stock" if is_avail else "out_of_stock")

                return {
                    "status": "success",
                    "price_usd": p_usd,
                    "availability": avail_status,
                    "elapsed_ms": round((time.perf_counter() - t_start) * 1000, 2)
                }

        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)
        
        content = page.content()
        if "Access Denied" in content:
            return {
                "status": "rate_limited",
                "price_usd": 0.0,
                "availability": "unknown",
                "elapsed_ms": round((time.perf_counter() - t_start) * 1000, 2),
                "error": "Akamai Access Denied"
            }
            
        # Price extraction: look for data-price or price under heading
        price_usd = 0.0
        p_match = re.search(r'data-price=\"([0-9\.]+)\"', content)
        if p_match:
            price_usd = float(p_match.group(1))
        else:
            # Anchor search under product title or maincontent to avoid header promo carousel trap
            mc_idx = content.find('maincontent')
            search_scope = content[mc_idx:] if mc_idx != -1 else content
            matches = re.findall(r'\$(\d+(?:\.\d{2})?)', search_scope[:5000])
            if matches:
                price_usd = float(matches[0])
                
        # Stock extraction
        avail = "in_stock"
        if "out of stock" in content.lower() or "sold out" in content.lower():
            avail = "out_of_stock"
            
        return {
            "status": "success",
            "price_usd": price_usd,
            "availability": avail,
            "elapsed_ms": round((time.perf_counter() - t_start) * 1000, 2)
        }
    except Exception as err:
        return {
            "status": "error",
            "price_usd": 0.0,
            "availability": "unknown",
            "elapsed_ms": round((time.perf_counter() - t_start) * 1000, 2),
            "error": str(err)
        }

