"""
Centralized Browser-Grade Network Utilities
Provides Chrome 133 fingerprinting headers, connection pooling limits, and HTTP clients.
Pure functions only, zero classes (ADR 0005, ADR 0010).
"""
from typing import Any, Dict, Optional
import httpx

CHROME_133_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
)

DEFAULT_BROWSER_HEADERS: Dict[str, str] = {
    "User-Agent": CHROME_133_USER_AGENT,
    "Sec-Ch-Ua": '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

DEFAULT_MAX_KEEPALIVE_CONNECTIONS = 5
DEFAULT_MAX_CONNECTIONS = 10
DEFAULT_TIMEOUT_SECONDS = 8.0
DEFAULT_CONNECT_TIMEOUT_SECONDS = 3.0


def get_browser_headers(custom_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Return modern Chrome 133 browser fingerprinting headers.
    Optionally merge or override with custom headers.
    """
    headers = dict(DEFAULT_BROWSER_HEADERS)
    if custom_headers:
        headers.update(custom_headers)
    return headers


def create_connection_limits(
    max_keepalive_connections: int = DEFAULT_MAX_KEEPALIVE_CONNECTIONS,
    max_connections: int = DEFAULT_MAX_CONNECTIONS
) -> httpx.Limits:
    """Create httpx.Limits with connection pool boundaries."""
    return httpx.Limits(
        max_keepalive_connections=max_keepalive_connections,
        max_connections=max_connections
    )


def create_http_client(
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    connect_timeout: float = DEFAULT_CONNECT_TIMEOUT_SECONDS,
    max_keepalive_connections: int = DEFAULT_MAX_KEEPALIVE_CONNECTIONS,
    max_connections: int = DEFAULT_MAX_CONNECTIONS,
    custom_headers: Optional[Dict[str, str]] = None,
    follow_redirects: bool = True
) -> httpx.Client:
    """
    Instantiate a configured httpx.Client with Chrome 133 headers and connection pooling limits.
    """
    headers = get_browser_headers(custom_headers)
    limits = create_connection_limits(
        max_keepalive_connections=max_keepalive_connections,
        max_connections=max_connections
    )
    timeout = httpx.Timeout(timeout_seconds, connect=connect_timeout)
    return httpx.Client(
        headers=headers,
        timeout=timeout,
        limits=limits,
        follow_redirects=follow_redirects
    )
