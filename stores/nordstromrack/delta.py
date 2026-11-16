"""
Store Delta Updater: Nordstrom Rack (Marc Jacobs & Kurt Geiger London Handbags)
Delegates price and stock verification to Camoufox Kasada solver engine.
Pure functions only, zero classes (ADR 0002, ADR 0005, ADR 0010).
"""
import os
import sys
from typing import Any, Dict, Optional
import httpx

from stores.nordstrom.delta import (
    check_price_and_stock as nordstrom_check_price_and_stock,
    apply_delta_to_product,
    norm_size_string
)

def check_price_and_stock(
    product: Dict[str, Any],
    client: Optional[httpx.Client] = None,
    store_name: str = "nordstromrack",
    rate_limiter: Optional[Any] = None,
    browser_page: Optional[Any] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Verify live price and stock availability for Nordstrom Rack products.
    """
    return nordstrom_check_price_and_stock(
        product=product,
        client=client,
        store_name=store_name,
        rate_limiter=rate_limiter,
        browser_page=browser_page,
        **kwargs
    )
