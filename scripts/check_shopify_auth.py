#!/usr/bin/env python3
"""
Diagnostic utility to inspect Shopify Admin API authentication status.
Introspects:
  - Permanent Custom App token in config/shopify_config.json
  - Environment variable SHOPIFY_ADMIN_ACCESS_TOKEN
  - Ephemeral Shopify CLI session token in %APPDATA%
  - Live API reachability via Admin GraphQL test query.
"""
import os
import sys
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import get_shopify_auth_status, execute_shopify_graphql, reset_auth_circuit_breaker

def run_diagnostics():
    print("=" * 70)
    print("SHOPIFY AUTHENTICATION DIAGNOSTICS & HEALTH CHECK")
    print("=" * 70)
    
    # Temporarily reset circuit breaker to test live reachability if requested
    reset_auth_circuit_breaker()
    status = get_shopify_auth_status()
    
    print(f"Store Domain:           {status.get('shop_domain')}")
    print(f"Active Token Source:    {status.get('active_source').upper()}")
    print(f"Has Active Token:       {status.get('has_token')}")
    print(f"Token Preview:          {status.get('token_preview') or 'None'}")
    print(f"Is Permanent Token:     {status.get('is_permanent')} (Custom App shpat_ never expires)")
    print(f"Config File Present:    {status.get('config_token_present')}")
    print(f"Env Variable Present:   {status.get('env_token_present')}")
    print(f"CLI Token In Store:     {status.get('cli_token_present')}")
    print(f"CLI Token Expired:      {status.get('cli_token_expired')}")
    if status.get('cli_expires_at'):
        print(f"CLI Expiration Time:    {status.get('cli_expires_at')}")
    print("-" * 70)

    if not status.get("has_token"):
        print("\n[!] STATUS: AUTHENTICATION REQUIRED")
        print("No active, non-expired Shopify Admin API token is currently available.")
        print("\nRECOMMENDED PERMANENT SOLUTION (Never expires, 0 manual logins):")
        print("  1. In Shopify Admin -> Settings -> Apps and sales channels -> Develop apps")
        print("     URL: https://admin.shopify.com/store/hewmvw-am/settings/apps/development")
        print("  2. Create an app named 'Rare Avenue Sync Engine'")
        print("  3. Grant Admin API scopes: write_products, read_products, write_themes, write_inventory")
        print("  4. Install app and copy Admin API access token (starts with shpat_...)")
        print("  5. Run: python scripts/setup_permanent_shopify_token.py --token <YOUR_TOKEN>")
        print("\nTEMPORARY CLI SOLUTION (Expires in ~24 hours):")
        print("  Run: shopify theme list --store=hewmvw-am.myshopify.com")
        print("  Complete browser login when prompted.")
        return False

    print("\n[+] Testing live GraphQL connection against Shopify Admin...")
    test_query = """
    query {
      shop {
        name
        myshopifyDomain
        plan {
          displayName
        }
      }
      currentAppInstallation {
        app {
          title
        }
        accessScopes {
          handle
        }
      }
    }
    """
    data, ext, err = execute_shopify_graphql(test_query)
    if data and data.get("shop"):
        shop = data["shop"]
        app_inst = data.get("currentAppInstallation") or {}
        scopes = [s["handle"] for s in app_inst.get("accessScopes", [])]
        print(f"[SUCCESS] Connected to live Shopify store!")
        print(f"  Shop Name:     {shop.get('name')}")
        print(f"  Domain:        {shop.get('myshopifyDomain')}")
        print(f"  Plan:          {shop.get('plan', {}).get('displayName')}")
        print(f"  App Title:     {app_inst.get('app', {}).get('title', 'Unknown')}")
        print(f"  Active Scopes: {scopes if scopes else 'None ([!] Scopes not yet granted)'}")

        required_scopes = {"write_products", "read_products", "write_themes", "read_themes", "write_inventory"}
        missing = required_scopes - set(scopes)
        if missing:
            print(f"\n[!] ACTION REQUIRED: App is missing scopes: {sorted(missing)}")
            print(f"To grant these scopes with 1 click, open this URL in your browser while logged into Shopify:")
            print(f"--> https://admin.shopify.com/store/hewmvw-am/oauth/authorize?client_id=5dadd21e620a72d0f0617d58bbd8c5b9&scope=write_products,read_products,write_themes,read_themes,write_inventory,read_inventory,write_files,read_files")
            print(f"Click 'Install app' or 'Update app' to grant all scopes.")
            return False
        return True
    else:
        print(f"[FAIL] Connection test failed: {err}")
        return False

if __name__ == "__main__":
    ok = run_diagnostics()
    sys.exit(0 if ok else 1)
