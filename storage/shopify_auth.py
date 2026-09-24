"""
Shopify Authentication & Dynamic Token Management
Dynamically resolves authenticated tokens from Shopify CLI session or config.
Pure functions only, zero classes (ADR 0005, ADR 0019).
"""
import os
import sys
import json
import time
from typing import Optional, Dict, Any, Tuple
import httpx

CLI_CONFIG_PATH = os.path.expandvars(r"%APPDATA%\shopify-cli-kit-nodejs\Config\config.json")
CONFIG_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "shopify_config.json")
DEFAULT_SHOP_DOMAIN = "hewmvw-am.myshopify.com"
DEFAULT_API_VERSION = "2026-04"


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


def execute_shopify_graphql(
    query: str,
    variables: Optional[Dict[str, Any]] = None,
    shop_domain: str = DEFAULT_SHOP_DOMAIN,
    timeout: float = 20.0
) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any], str]:
    """
    Execute GraphQL query or mutation against Shopify Admin GraphQL API.
    Returns (data_dict, extensions_dict, error_message).
    """
    domain, token, version = get_shopify_credentials(shop_domain)
    if not token:
        return None, {}, "No valid Shopify access token found. Please authenticate via Shopify CLI."

    url = f"https://{domain}/admin/api/{version}/graphql.json"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    payload: Dict[str, Any] = {"query": query}
    if variables:
        payload["variables"] = variables

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                body = resp.json()
                data = body.get("data")
                extensions = body.get("extensions", {})
                errors = body.get("errors")
                if errors:
                    err_msg = json.dumps(errors)
                    return data, extensions, f"GraphQL Errors: {err_msg}"
                return data, extensions, ""
            else:
                return None, {}, f"HTTP {resp.status_code}: {resp.text}"
    except Exception as exc:
        return None, {}, f"Request Exception: {exc}"
