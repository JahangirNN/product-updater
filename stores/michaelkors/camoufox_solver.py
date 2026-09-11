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
    """
    t_start = time.perf_counter()
    try:
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
            
        # Price extraction: look for data-price or $XX
        price_usd = 0.0
        p_match = re.search(r'data-price=\"([0-9\.]+)\"', content)
        if p_match:
            price_usd = float(p_match.group(1))
        else:
            matches = re.findall(r'\$(\d+(?:\.\d{2})?)', content)
            if matches:
                price_usd = float(matches[-1])
                
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
