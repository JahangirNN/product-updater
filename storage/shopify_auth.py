"""
Shopify Authentication & Auto-Refreshing Token Management
Dynamically resolves authenticated tokens from Shopify CLI session or config.
Automatically triggers CLI session refresh on token expiration (ADR 0005, ADR 0019).
Pure functions only, zero classes.
"""
import os
import sys
import json
import time
import subprocess
from typing import Optional, Dict, Any, Tuple
import httpx

from storage.logger import log_shopify_error, log_shopify_warning

CLI_CONFIG_PATH = os.path.expandvars(r"%APPDATA%\shopify-cli-kit-nodejs\Config\config.json")
CONFIG_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "shopify_config.json")
DEFAULT_SHOP_DOMAIN = "hewmvw-am.myshopify.com"
DEFAULT_API_VERSION = "2026-04"


_LAST_CLI_REFRESH_TIME: float = 0.0
_CLI_REFRESH_COOLDOWN_SECONDS: float = 300.0  # 5-minute cooldown between CLI refresh attempts


def refresh_cli_session(shop_domain: str = DEFAULT_SHOP_DOMAIN) -> bool:
    """Trigger Shopify CLI to refresh session tokens silently via CLI with cooldown to prevent blocking."""
    global _LAST_CLI_REFRESH_TIME
    now = time.time()
    if now - _LAST_CLI_REFRESH_TIME < _CLI_REFRESH_COOLDOWN_SECONDS:
        return False
    _LAST_CLI_REFRESH_TIME = now
    try:
        cmd = ["shopify.cmd" if sys.platform == "win32" else "shopify", "theme", "list", f"--store={shop_domain}"]
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=5
        )
        if res.returncode != 0:
            log_shopify_warning(f"Shopify CLI token auto-refresh exited with code {res.returncode}: {res.stderr.strip()[:200]}")
        return res.returncode == 0
    except subprocess.TimeoutExpired:
        log_shopify_warning(f"Shopify CLI token auto-refresh timed out after 5s for {shop_domain} (manual interactive login required).")
        return False
    except Exception as exc:
        log_shopify_warning(f"Shopify CLI token auto-refresh exception: {exc}")
        return False


def get_shopify_credentials(shop_domain: str = DEFAULT_SHOP_DOMAIN) -> Tuple[str, str, str]:
    """
    Retrieve active (shop_domain, access_token, api_version).
    Checks CLI session store first for auto-refreshed session tokens,
    falling back to static config/shopify_config.json.
    """
    if os.path.exists(CLI_CONFIG_PATH):
        try:
            with open(CLI_CONFIG_PATH, "r", encoding="utf-8") as f:
                cli_data = json.load(f)
            session_raw = cli_data.get("sessionStore")
            if session_raw:
                sessions = json.loads(session_raw) if isinstance(session_raw, str) else session_raw
                acc = sessions.get("accounts.shopify.com", {})
                apps = acc.get("applications", {})
                for app_k, app_v in apps.items():
                    if shop_domain in app_k and app_v.get("accessToken"):
                        token = app_v.get("accessToken")
                        return shop_domain, token, DEFAULT_API_VERSION
                for app_k, app_v in apps.items():
                    if app_v.get("accessToken"):
                        return shop_domain, app_v.get("accessToken"), DEFAULT_API_VERSION
        except Exception:
            pass

    if os.path.exists(CONFIG_FILE_PATH):
        try:
            with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            return (
                cfg.get("shop_domain", shop_domain),
                cfg.get("access_token", ""),
                cfg.get("api_version", DEFAULT_API_VERSION)
            )
        except Exception:
            pass

    env_token = os.environ.get("SHOPIFY_ADMIN_ACCESS_TOKEN", "")
    env_domain = os.environ.get("SHOPIFY_STORE_DOMAIN", shop_domain)
    return env_domain, env_token, DEFAULT_API_VERSION


_CLIENT: Optional[httpx.Client] = None


def get_shopify_http_client() -> httpx.Client:
    global _CLIENT
    if _CLIENT is None or _CLIENT.is_closed:
        _CLIENT = httpx.Client(
            timeout=35.0,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50, keepalive_expiry=60.0)
        )
    return _CLIENT


def execute_shopify_graphql(
    query: str,
    variables: Optional[Dict[str, Any]] = None,
    shop_domain: str = DEFAULT_SHOP_DOMAIN,
    timeout: float = 35.0,
    allow_retry: bool = True,
    max_retries: int = 4
) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any], str]:
    """
    Execute GraphQL query or mutation against Shopify Admin GraphQL API.
    Auto-refreshes CLI session token if expired (HTTP 401).
    Automatically backs off and retries on rate limits (HTTP 429 or GraphQL THROTTLED).
    Returns (data_dict, extensions_dict, error_message).
    """
    domain, token, version = get_shopify_credentials(shop_domain)
    if not token:
        if allow_retry and refresh_cli_session(domain):
            return execute_shopify_graphql(query, variables, shop_domain, timeout, allow_retry=False)
        err_msg = "No valid Shopify access token found. Please authenticate via Shopify CLI."
        log_shopify_error(err_msg)
        return None, {}, err_msg

    url = f"https://{domain}/admin/api/{version}/graphql.json"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    payload: Dict[str, Any] = {"query": query}
    if variables:
        payload["variables"] = variables

    client = get_shopify_http_client()

    for attempt in range(max_retries):
        try:
            resp = client.post(url, json=payload, headers=headers)

            # Handle token expiration with transparent auto-refresh or fail fast
            if resp.status_code == 401:
                if allow_retry and attempt == 0:
                    log_shopify_warning(f"Shopify Admin GraphQL returned 401 Unauthorized for {domain}. Triggering CLI session auto-refresh...")
                    if refresh_cli_session(domain):
                        return execute_shopify_graphql(query, variables, shop_domain, timeout, allow_retry=False)
                err_msg = f"HTTP 401 Unauthorized: Shopify session token expired for {domain}"
                log_shopify_error(err_msg)
                return None, {}, err_msg

            if (resp.status_code == 429 or resp.status_code == 503) and attempt < max_retries - 1:
                backoff = 2.5 * (attempt + 1)
                log_shopify_warning(f"Shopify Admin GraphQL HTTP {resp.status_code} for {domain}. Backing off {backoff:.1f}s (attempt {attempt+1}/{max_retries})...")
                time.sleep(backoff)
                continue

            if resp.status_code == 200:
                body = resp.json()
                data = body.get("data")
                extensions = body.get("extensions", {})
                errors = body.get("errors")
                if errors:
                    is_throttled = any("throttled" in str(e).lower() for e in errors)
                    if is_throttled and attempt < max_retries - 1:
                        backoff = 3.0 * (attempt + 1)
                        log_shopify_warning(f"Shopify Admin GraphQL THROTTLED for {domain}. Backing off {backoff:.1f}s (attempt {attempt+1}/{max_retries})...")
                        time.sleep(backoff)
                        continue
                    err_msg = json.dumps(errors)
                    log_shopify_error(f"Shopify Admin GraphQL returned errors: {err_msg}")
                    return data, extensions, f"GraphQL Errors: {err_msg}"
                return data, extensions, ""
            else:
                err_msg = f"HTTP {resp.status_code}: {resp.text}"
                log_shopify_error(f"Shopify Admin GraphQL failure: {err_msg}")
                return None, {}, err_msg
        except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.RemoteProtocolError, httpx.ConnectError, ConnectionResetError) as te:
            # Force client reset so subsequent attempts get a fresh TCP connection
            global _CLIENT
            try:
                if _CLIENT:
                    _CLIENT.close()
            except Exception:
                pass
            _CLIENT = None

            if attempt < max_retries - 1:
                backoff = 2.0 * (attempt + 1)
                log_shopify_warning(f"Shopify Admin GraphQL network blip ({type(te).__name__}: {te}). Reconnecting in {backoff:.1f}s (attempt {attempt+1}/{max_retries})...")
                time.sleep(backoff)
                client = get_shopify_http_client()
                continue
            err_msg = f"Network Disconnect / Timeout after {max_retries} attempts: {te}"
            log_shopify_error(f"Shopify Admin GraphQL network failure: {err_msg}", exc=te)
            return None, {}, err_msg
        except Exception as exc:
            # Check if inner exception was RemoteProtocolError or connection reset
            exc_str = str(exc).lower()
            if any(term in exc_str for term in ["disconnected", "connection reset", "10054", "remoteprotocolerror"]):
                try:
                    if _CLIENT:
                        _CLIENT.close()
                except Exception:
                    pass
                _CLIENT = None
                if attempt < max_retries - 1:
                    backoff = 2.0 * (attempt + 1)
                    log_shopify_warning(f"Shopify Admin GraphQL connection reset ({exc}). Reconnecting in {backoff:.1f}s (attempt {attempt+1}/{max_retries})...")
                    time.sleep(backoff)
                    client = get_shopify_http_client()
                    continue
            err_msg = f"Request Exception: {exc}"
            log_shopify_error(f"Shopify Admin GraphQL exception: {err_msg}", exc=exc)
            return None, {}, err_msg
