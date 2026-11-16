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
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple
import httpx

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from storage.logger import log_shopify_error, log_shopify_warning

CLI_CONFIG_PATH = os.path.expandvars(r"%APPDATA%\shopify-cli-kit-nodejs\Config\config.json")
CONFIG_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "shopify_config.json")
DEFAULT_SHOP_DOMAIN = "hewmvw-am.myshopify.com"
DEFAULT_API_VERSION = "2026-04"

_LAST_CLI_REFRESH_TIME: float = 0.0
_CLI_REFRESH_COOLDOWN_SECONDS: float = 300.0  # 5-minute cooldown between CLI refresh attempts

_AUTH_CIRCUIT_BREAKER_UNTIL: float = 0.0
_AUTH_CIRCUIT_BREAKER_COOLDOWN: float = 300.0  # 5-minute circuit breaker on 401

_CLIENT_CREDENTIALS_CACHE: Dict[str, Any] = {
    "access_token": "",
    "expires_at": 0.0,
    "scope": ""
}


def is_auth_circuit_breaker_active() -> bool:
    """Check if authentication circuit breaker is currently active."""
    global _AUTH_CIRCUIT_BREAKER_UNTIL
    return time.time() < _AUTH_CIRCUIT_BREAKER_UNTIL


def trip_auth_circuit_breaker(cooldown_seconds: float = _AUTH_CIRCUIT_BREAKER_COOLDOWN) -> None:
    """Trip authentication circuit breaker to prevent rapid error spamming."""
    global _AUTH_CIRCUIT_BREAKER_UNTIL
    _AUTH_CIRCUIT_BREAKER_UNTIL = time.time() + cooldown_seconds


def reset_auth_circuit_breaker() -> None:
    """Reset authentication circuit breaker on successful authentication."""
    global _AUTH_CIRCUIT_BREAKER_UNTIL
    _AUTH_CIRCUIT_BREAKER_UNTIL = 0.0


def get_client_app_credentials(shop_domain: str = DEFAULT_SHOP_DOMAIN) -> Tuple[str, str]:
    """Retrieve (client_id, client_secret) from environment variables or shopify_config.json."""
    client_id = os.environ.get("SHOPIFY_CLIENT_ID", "").strip()
    client_secret = os.environ.get("SHOPIFY_CLIENT_SECRET", "").strip()
    if client_id and client_secret:
        return client_id, client_secret

    if os.path.exists(CONFIG_FILE_PATH):
        try:
            with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            client_id = client_id or cfg.get("client_id", "").strip()
            client_secret = client_secret or cfg.get("client_secret", "").strip()
            if client_id and client_secret:
                return client_id, client_secret
        except Exception:
            pass

    return "", ""


def fetch_token_via_client_credentials(
    shop_domain: str = DEFAULT_SHOP_DOMAIN,
    force_refresh: bool = False
) -> Tuple[str, str]:
    """
    Programmatically obtain an Admin API access token using Shopify Client Credentials Grant:
    POST https://{shop_domain}/admin/oauth/access_token
    Payload: client_id, client_secret, grant_type='client_credentials'
    Auto-refreshes seamlessly whenever the 24-hour token nears expiration (300s buffer).
    Returns (access_token, error_message).
    """
    global _CLIENT_CREDENTIALS_CACHE
    now = time.time()
    if not force_refresh and _CLIENT_CREDENTIALS_CACHE.get("access_token") and now < _CLIENT_CREDENTIALS_CACHE.get("expires_at", 0.0):
        return _CLIENT_CREDENTIALS_CACHE["access_token"], ""

    client_id, client_secret = get_client_app_credentials(shop_domain)
    if not client_id or not client_secret:
        return "", "SHOPIFY_CLIENT_ID or SHOPIFY_CLIENT_SECRET not configured in environment or config"

    url = f"https://{shop_domain}/admin/oauth/access_token"
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials"
    }

    try:
        with httpx.Client(timeout=20.0) as oauth_client:
            resp = oauth_client.post(url, json=payload, headers={"Content-Type": "application/json"})
            if resp.status_code == 200:
                data = resp.json()
                token = data.get("access_token", "").strip()
                expires_in = data.get("expires_in", 86400)
                scope = data.get("scope", "")
                if token:
                    _CLIENT_CREDENTIALS_CACHE["access_token"] = token
                    _CLIENT_CREDENTIALS_CACHE["expires_at"] = now + max(60, expires_in - 300)
                    _CLIENT_CREDENTIALS_CACHE["scope"] = scope
                    reset_auth_circuit_breaker()
                    return token, ""
                return "", "Shopify Client Credentials returned 200 but missing access_token in body"
            else:
                return "", f"Shopify Client Credentials HTTP {resp.status_code}: {resp.text[:300]}"
    except Exception as exc:
        return "", f"Shopify Client Credentials network exception: {exc}"


def refresh_cli_session(shop_domain: str = DEFAULT_SHOP_DOMAIN) -> bool:
    """
    Shopify CLI sessions require interactive browser OAuth when expired.
    Silent background processes cannot complete browser authentication.
    Returns False immediately to prevent hanging, and advises on permanent resolution.
    """
    log_shopify_warning(
        f"Shopify CLI session token expired for {shop_domain}. "
        f"Interactive login required via 'shopify theme list --store={shop_domain}', "
        f"or configure Custom App client credentials in .env (recommended, auto-refreshed)."
    )
    return False


def get_shopify_credentials(shop_domain: str = DEFAULT_SHOP_DOMAIN) -> Tuple[str, str, str]:
    """
    Retrieve active (shop_domain, access_token, api_version).
    Hierarchical resolution:
    1. Dynamic Client Credentials Grant from SHOPIFY_CLIENT_ID + SHOPIFY_CLIENT_SECRET (auto-refreshes seamlessly, highest priority).
    2. Static Custom App token from config/shopify_config.json (access_token).
    3. Static Custom App token from SHOPIFY_ADMIN_ACCESS_TOKEN environment variable.
    4. Dynamic CLI session token from %APPDATA% (validated against expiresAt timestamp).
    """
    # 1. Dynamic Client Credentials Grant (Headless, 0 manual logins, auto-refreshed)
    client_id, client_secret = get_client_app_credentials(shop_domain)
    if client_id and client_secret:
        token, err = fetch_token_via_client_credentials(shop_domain)
        if token:
            api_ver = os.environ.get("SHOPIFY_API_VERSION", DEFAULT_API_VERSION)
            return shop_domain, token, api_ver
        else:
            log_shopify_warning(f"Client credentials exchange failed: {err}. Falling back to static/CLI tokens.")

    # 2. Static config file (Permanent Custom App Admin API token)
    if os.path.exists(CONFIG_FILE_PATH):
        try:
            with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            static_token = cfg.get("access_token", "").strip()
            if static_token:
                return (
                    cfg.get("shop_domain", shop_domain),
                    static_token,
                    cfg.get("api_version", DEFAULT_API_VERSION)
                )
        except Exception as exc:
            log_shopify_warning(f"Error reading {CONFIG_FILE_PATH}: {exc}")

    # 3. Environment variable
    env_token = os.environ.get("SHOPIFY_ADMIN_ACCESS_TOKEN", "").strip()
    if env_token:
        env_domain = os.environ.get("SHOPIFY_STORE_DOMAIN", shop_domain)
        return env_domain, env_token, os.environ.get("SHOPIFY_API_VERSION", DEFAULT_API_VERSION)

    # 3. CLI session store with expiresAt validation
    if os.path.exists(CLI_CONFIG_PATH):
        try:
            with open(CLI_CONFIG_PATH, "r", encoding="utf-8") as f:
                cli_data = json.load(f)
            session_raw = cli_data.get("sessionStore")
            if session_raw:
                sessions = json.loads(session_raw) if isinstance(session_raw, str) else session_raw
                acc = sessions.get("accounts.shopify.com", {})
                apps = acc.get("applications", {})

                matched_apps = []
                for app_k, app_v in apps.items():
                    if shop_domain in app_k and app_v.get("accessToken"):
                        matched_apps.insert(0, (app_k, app_v))
                    elif app_v.get("accessToken"):
                        matched_apps.append((app_k, app_v))

                now_utc = datetime.now(timezone.utc)
                for app_k, app_v in matched_apps:
                    token = app_v.get("accessToken", "").strip()
                    expires_at_str = app_v.get("expiresAt")
                    if not token:
                        continue

                    is_expired = False
                    if expires_at_str:
                        try:
                            clean_iso = expires_at_str.replace("Z", "+00:00")
                            exp_dt = datetime.fromisoformat(clean_iso)
                            if now_utc >= exp_dt:
                                is_expired = True
                        except Exception:
                            pass

                    if not is_expired:
                        return shop_domain, token, DEFAULT_API_VERSION
        except Exception as exc:
            log_shopify_warning(f"Error reading CLI session config: {exc}")

    return shop_domain, "", DEFAULT_API_VERSION


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
    if is_auth_circuit_breaker_active():
        remaining = max(0, int(_AUTH_CIRCUIT_BREAKER_UNTIL - time.time()))
        err_msg = (
            f"HTTP 401 Unauthorized: Shopify authentication circuit-breaker active ({remaining}s remaining). "
            f"Please configure a permanent Custom App token in config/shopify_config.json or re-authenticate via Shopify CLI."
        )
        return None, {}, err_msg

    domain, token, version = get_shopify_credentials(shop_domain)
    if not token:
        if allow_retry and refresh_cli_session(domain):
            return execute_shopify_graphql(query, variables, shop_domain, timeout, allow_retry=False)
        trip_auth_circuit_breaker(cooldown_seconds=300.0)
        err_msg = (
            f"No valid Shopify access token found for {domain}. "
            f"Please configure a permanent Custom App token in config/shopify_config.json "
            f"(recommended, never expires) or re-authenticate via Shopify CLI."
        )
        log_shopify_error(err_msg)
        return None, {}, err_msg

    url = f"https://{domain}/admin/api/{version}/graphql.json"
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": token
    }

    payload: Dict[str, Any] = {"query": query}
    if variables:
        payload["variables"] = variables

    client = get_shopify_http_client()

    for attempt in range(max_retries):
        try:
            resp = client.post(url, json=payload, headers=headers)

            # Handle token expiration with transparent auto-refresh or fail fast with circuit breaker
            if resp.status_code == 401:
                cid, csec = get_client_app_credentials(domain)
                if cid and csec and allow_retry:
                    log_shopify_warning(
                        f"Shopify Admin GraphQL HTTP 401 for {domain}. "
                        f"Auto-refreshing session token via Client Credentials Grant..."
                    )
                    new_token, auth_err = fetch_token_via_client_credentials(domain, force_refresh=True)
                    if new_token:
                        return execute_shopify_graphql(query, variables, shop_domain, timeout, allow_retry=False)
                    else:
                        log_shopify_error(f"Failed to auto-refresh token via Client Credentials: {auth_err}")

                trip_auth_circuit_breaker(cooldown_seconds=300.0)
                err_msg = (
                    f"HTTP 401 Unauthorized: Shopify session token expired for {domain}. "
                    f"Tripped 5-minute auth circuit breaker. "
                    f"Action: Verify Custom App client credentials or grant permissions in Shopify Developer Dashboard."
                )
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
                reset_auth_circuit_breaker()
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


def get_shopify_auth_status(shop_domain: str = DEFAULT_SHOP_DOMAIN) -> Dict[str, Any]:
    """Inspect all credential sources and report health, expiration, and active source."""
    status: Dict[str, Any] = {
        "shop_domain": shop_domain,
        "active_source": "none",
        "has_token": False,
        "token_preview": None,
        "is_permanent": False,
        "client_credentials_configured": False,
        "client_credentials_scopes": None,
        "cli_token_present": False,
        "cli_token_expired": False,
        "cli_expires_at": None,
        "config_token_present": False,
        "env_token_present": False,
        "circuit_breaker_active": is_auth_circuit_breaker_active(),
        "circuit_breaker_remaining_seconds": max(0, int(_AUTH_CIRCUIT_BREAKER_UNTIL - time.time()))
    }

    # 1. Check Client Credentials Grant (Highest priority)
    cid, csec = get_client_app_credentials(shop_domain)
    if cid and csec:
        status["client_credentials_configured"] = True
        tok, err = fetch_token_via_client_credentials(shop_domain)
        if tok:
            status["active_source"] = "client_credentials"
            status["has_token"] = True
            status["token_preview"] = f"{tok[:8]}...{tok[-4:]}"
            status["is_permanent"] = True
            status["client_credentials_scopes"] = _CLIENT_CREDENTIALS_CACHE.get("scope", "")
            return status

    # 2. Check config file (Permanent Custom App Admin API token)
    if os.path.exists(CONFIG_FILE_PATH):
        try:
            with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            t = cfg.get("access_token", "").strip()
            if t:
                status["config_token_present"] = True
                status["active_source"] = "config_file"
                status["has_token"] = True
                status["token_preview"] = f"{t[:8]}...{t[-4:]}"
                status["is_permanent"] = True
                return status
        except Exception:
            pass

    # 2. Check environment variable
    env_t = os.environ.get("SHOPIFY_ADMIN_ACCESS_TOKEN", "").strip()
    if env_t:
        status["env_token_present"] = True
        status["active_source"] = "environment"
        status["has_token"] = True
        status["token_preview"] = f"{env_t[:8]}...{env_t[-4:]}"
        status["is_permanent"] = True
        return status

    # 3. Check CLI store
    if os.path.exists(CLI_CONFIG_PATH):
        try:
            with open(CLI_CONFIG_PATH, "r", encoding="utf-8") as f:
                cli_data = json.load(f)
            session_raw = cli_data.get("sessionStore")
            if session_raw:
                sessions = json.loads(session_raw) if isinstance(session_raw, str) else session_raw
                acc = sessions.get("accounts.shopify.com", {})
                apps = acc.get("applications", {})
                now_utc = datetime.now(timezone.utc)
                for app_k, app_v in apps.items():
                    tok = app_v.get("accessToken", "").strip()
                    exp = app_v.get("expiresAt")
                    if tok:
                        status["cli_token_present"] = True
                        status["cli_expires_at"] = exp
                        is_exp = False
                        if exp:
                            try:
                                exp_dt = datetime.fromisoformat(exp.replace("Z", "+00:00"))
                                is_exp = (now_utc >= exp_dt)
                            except Exception:
                                pass
                        status["cli_token_expired"] = is_exp
                        if not is_exp:
                            status["active_source"] = "shopify_cli"
                            status["has_token"] = True
                            status["token_preview"] = f"{tok[:8]}...{tok[-4:]}"
                            status["is_permanent"] = False
                            return status
        except Exception:
            pass

    return status


def save_permanent_token(
    token: str,
    shop_domain: str = DEFAULT_SHOP_DOMAIN,
    api_version: str = DEFAULT_API_VERSION
) -> bool:
    """Save a permanent Custom App Admin API token into config/shopify_config.json and reset circuit breaker."""
    os.makedirs(os.path.dirname(CONFIG_FILE_PATH), exist_ok=True)
    cfg = {
        "shop_domain": shop_domain,
        "access_token": token.strip(),
        "api_version": api_version,
        "configured_at": datetime.now(timezone.utc).isoformat(),
        "note": "Permanent Custom App Admin API token - does not expire."
    }
    with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    reset_auth_circuit_breaker()
    return True
