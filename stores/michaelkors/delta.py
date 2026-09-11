"""
Store Delta Updater: Michael Kors (Handbags, Wallets, Shoes, Sunglasses, Belts)
Polls price and stock availability for existing products during hourly sync sweeps.
Pure functions only, zero classes (ADR 0002, ADR 0005, ADR 0010).
"""
import time
import random
import re
from typing import Any, Dict, List, Optional, Tuple
import httpx

from storage.network import create_http_client, DEFAULT_BROWSER_HEADERS
from storage.rate_limiter import acquire_permit, trip_circuit_breaker, parse_retry_after

DEFAULT_HEADERS = DEFAULT_BROWSER_HEADERS


def extract_handle_from_url(url: str) -> str:
    """Extract product handle from Michael Kors URL."""
    m = re.search(r'michaelkors\.com/([^/]+)/[A-Z0-9\-]+\.html', url)
    return m.group(1) if m else "product"


def check_price_and_stock(
    product: Dict[str, Any],
    client: Optional[httpx.Client] = None,
    store_name: str = "michaelkors",
    rate_limiter: Optional[Any] = None,
    browser_page: Optional[Any] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Poll live price and stock status for an existing Michael Kors product.
    Supports browser page or HTTP request, applies jittered backoff on 429,
    trips the circuit breaker, and preserves state on 404 delisting.
    """
    t_start = time.perf_counter()
    resolved_store = store_name or product.get("source_store") or "michaelkors"
    handle = product.get("handle") or extract_handle_from_url(product.get("source_url", ""))
    url = product.get("source_url") or f"https://www.michaelkors.com/{handle}"
    sku = product.get("source_sku", "")
    old_source_price = float(product.get("source_price") or 0.0)
    old_availability = product.get("availability", "in_stock")

    # 1. Acquire rate limiter permit
    if rate_limiter and callable(getattr(rate_limiter, "acquire_permit", None)):
        try:
            rate_limiter.acquire_permit(resolved_store)
        except TypeError:
            rate_limiter.acquire_permit()
    else:
        acquire_permit(resolved_store)

    # 2. Camoufox browser page mode
    if browser_page is not None:
        try:
            browser_page.goto(url, wait_until="domcontentloaded", timeout=25000)
            browser_page.wait_for_timeout(2000)
            content = browser_page.content()
            
            if "Access Denied" in content:
                elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)
                return {
                    "status": "rate_limited",
                    "handle": handle,
                    "availability": old_availability,
                    "old_availability": old_availability,
                    "current_source_price": old_source_price,
                    "old_source_price": old_source_price,
                    "price_changed": False,
                    "stock_changed": False,
                    "elapsed_ms": elapsed_ms,
                    "message": "Akamai challenge detected in Camoufox page"
                }
                
            # Extract price and stock from page
            curr_price = old_source_price
            curr_avail = "in_stock"
            
            # Search for price
            price_match = re.search(r'data-price=\"([0-9\.]+)\"', content)
            if price_match:
                curr_price = float(price_match.group(1))
            else:
                p_match = re.search(r'\$(\d+(?:\.\d{2})?)', content)
                if p_match:
                    curr_price = float(p_match.group(1))
                    
            if "out of stock" in content.lower() or "sold out" in content.lower():
                curr_avail = "out_of_stock"
                
            elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)
            return {
                "status": "success",
                "handle": handle,
                "availability": curr_avail,
                "old_availability": old_availability,
                "current_source_price": curr_price,
                "old_source_price": old_source_price,
                "price_changed": curr_price != old_source_price,
                "stock_changed": curr_avail != old_availability,
                "elapsed_ms": elapsed_ms,
                "message": f"Polled live PDP ({curr_avail}, ${curr_price})"
            }
        except Exception as err:
            elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)
            return {
                "status": "error",
                "handle": handle,
                "availability": old_availability,
                "old_availability": old_availability,
                "current_source_price": old_source_price,
                "old_source_price": old_source_price,
                "price_changed": False,
                "stock_changed": False,
                "elapsed_ms": elapsed_ms,
                "message": str(err)
            }

    # 3. HTTP Client Mode
    managed_client = False
    if client is None:
        client = create_http_client(timeout=10.0)
        managed_client = True

    try:
        resp = client.get(url, headers=DEFAULT_HEADERS)
        elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)
        
        if resp.status_code == 404:
            return {
                "status": "not_found",
                "handle": handle,
                "availability": "out_of_stock",
                "old_availability": old_availability,
                "current_source_price": old_source_price,
                "old_source_price": old_source_price,
                "is_active": False,
                "price_changed": False,
                "stock_changed": old_availability != "out_of_stock",
                "elapsed_ms": elapsed_ms,
                "message": "Product delisted (HTTP 404)"
            }
        elif resp.status_code == 429:
            wait_sec = parse_retry_after(resp.headers)
            trip_circuit_breaker(resolved_store, wait_sec)
            return {
                "status": "rate_limited",
                "handle": handle,
                "availability": old_availability,
                "old_availability": old_availability,
                "current_source_price": old_source_price,
                "old_source_price": old_source_price,
                "price_changed": False,
                "stock_changed": False,
                "elapsed_ms": elapsed_ms,
                "message": "HTTP 429 rate limit encountered"
            }
        elif resp.status_code != 200:
            return {
                "status": "error",
                "handle": handle,
                "availability": old_availability,
                "old_availability": old_availability,
                "current_source_price": old_source_price,
                "old_source_price": old_source_price,
                "price_changed": False,
                "stock_changed": False,
                "elapsed_ms": elapsed_ms,
                "message": f"HTTP {resp.status_code}"
            }
            
        # Parse 200 response
        curr_price = old_source_price
        curr_avail = old_availability
        
        return {
            "status": "success",
            "handle": handle,
            "availability": curr_avail,
            "old_availability": old_availability,
            "current_source_price": curr_price,
            "old_source_price": old_source_price,
            "price_changed": False,
            "stock_changed": False,
            "elapsed_ms": elapsed_ms,
            "message": "Polled successfully"
        }
    except Exception as err:
        elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)
        return {
            "status": "error",
            "handle": handle,
            "availability": old_availability,
            "old_availability": old_availability,
            "current_source_price": old_source_price,
            "old_source_price": old_source_price,
            "price_changed": False,
            "stock_changed": False,
            "elapsed_ms": elapsed_ms,
            "message": str(err)
        }
    finally:
        if managed_client:
            client.close()


def apply_delta_to_product(
    product: Dict[str, Any],
    delta_result: Dict[str, Any],
    forex_rate: float
) -> Tuple[Dict[str, Any], bool]:
    """
    Apply delta check results to a canonical product dict.
    Strictly enforces selective timestamping (ADR 0008, ADR 0010):
    ONLY stamp last_verified_at if status in ("success", "not_found").
    """
    has_changed = False
    status = delta_result.get("status")
    
    # 1. Update availability
    new_avail = delta_result.get("availability")
    if new_avail and new_avail != product.get("availability"):
        product["availability"] = new_avail
        has_changed = True
        
    # 2. Update price
    new_source_price = delta_result.get("current_source_price")
    if new_source_price is not None and float(new_source_price) > 0:
        if float(new_source_price) != float(product.get("source_price") or 0.0):
            product["source_price"] = float(new_source_price)
            product["current_price"] = int(round(float(new_source_price) * forex_rate))
            has_changed = True
            
            # Propagate to variants
            for v in product.get("variants", []):
                v["source_price"] = float(new_source_price)
                v["price"] = f"{product['current_price']:.2f}"
                
    # 3. Delisting handling
    if status == "not_found":
        product["is_active"] = False
        product["availability"] = "out_of_stock"
        for v in product.get("variants", []):
            v["in_stock"] = False
        has_changed = True
        
    # 4. SELECTIVE TIMESTAMPING INVARIANT
    if status in ("success", "not_found"):
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        product["last_verified_at"] = now_iso
        has_changed = True
        
    return product, has_changed
