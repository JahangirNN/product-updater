#!/usr/bin/env python3
"""
Sets up and validates a permanent Custom App Admin API token for The Rare Avenue.
Validates the token against live Shopify Admin GraphQL before saving to config/shopify_config.json.
Drains any pending delta sync events once authenticated.
"""
import os
import sys
import argparse
import httpx

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import save_permanent_token, reset_auth_circuit_breaker, DEFAULT_SHOP_DOMAIN, DEFAULT_API_VERSION
from storage.shopify_sync import drain_delta_events_queue

def test_token(token: str, shop_domain: str, api_version: str):
    """Test token validity against Shopify Admin GraphQL."""
    url = f"https://{shop_domain}/admin/api/{api_version}/graphql.json"
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": token,
        "Authorization": f"Bearer {token}"
    }
    query = "query { shop { name myshopifyDomain } }"
    with httpx.Client(timeout=15.0) as client:
        resp = client.post(url, json={"query": query}, headers=headers)
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            shop = data.get("shop")
            if shop:
                return True, shop.get("name")
        return False, f"HTTP {resp.status_code}: {resp.text[:200]}"

def main():
    parser = argparse.ArgumentParser(description="Configure permanent Shopify Custom App token")
    parser.add_argument("--token", type=str, help="Shopify Admin API access token (e.g. shpat_...)")
    parser.add_argument("--store", type=str, default=DEFAULT_SHOP_DOMAIN, help="Shopify myshopify.com domain")
    parser.add_argument("--api-version", type=str, default=DEFAULT_API_VERSION, help="Admin API version")
    parser.add_argument("--no-drain", action="store_true", help="Skip draining pending delta events")
    args = parser.parse_args()

    token = args.token
    if not token:
        print("Enter Shopify Admin API Access Token (starts with shpat_...):")
        token = input().strip()

    if not token:
        print("[ERROR] Token cannot be empty.")
        sys.exit(1)

    print(f"\n[1/3] Validating token against https://{args.store}/admin/api/{args.api_version}...")
    valid, info = test_token(token, args.store, args.api_version)
    if not valid:
        print(f"[ERROR] Token validation failed: {info}")
        print("Please check that the token has required scopes (write_products, read_products, write_themes).")
        sys.exit(1)

    print(f"[2/3] Validation successful! Connected to shop: '{info}'.")
    save_permanent_token(token, args.store, args.api_version)
    print(f"      Saved permanent credentials to config/shopify_config.json.")

    if not args.no_drain:
        print(f"[3/3] Draining pending delta events queue...")
        drain_res = drain_delta_events_queue()
        print(f"      Queue sweep complete: {drain_res}")

    print("\n[SUCCESS] Shopify authentication is now permanently configured!")
    print("The freshner daemon and all sync scripts will run indefinitely with 0 token expirations.")

if __name__ == "__main__":
    main()
