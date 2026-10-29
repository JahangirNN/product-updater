#!/usr/bin/env python3
"""
Interactive helper to refresh Shopify CLI session tokens via browser OAuth.
Runs 'shopify theme list' which triggers the official browser authorization flow.
"""
import os
import sys
import subprocess

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import DEFAULT_SHOP_DOMAIN, reset_auth_circuit_breaker

def main():
    store = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SHOP_DOMAIN
    print("=" * 70)
    print("SHOPIFY CLI INTERACTIVE RE-LOGIN")
    print(f"Store: {store}")
    print("=" * 70)
    print("Opening browser for Shopify OAuth login...")
    print("Please approve the connection in your browser window.")
    
    cmd = ["shopify.cmd" if sys.platform == "win32" else "shopify", "theme", "list", f"--store={store}"]
    try:
        res = subprocess.run(cmd)
        if res.returncode == 0:
            reset_auth_circuit_breaker()
            print("\n[SUCCESS] Shopify CLI session successfully refreshed!")
            print("Session token stored in %APPDATA%\\shopify-cli-kit-nodejs\\Config\\config.json.")
        else:
            print(f"\n[ERROR] CLI login process exited with code {res.returncode}")
    except Exception as e:
        print(f"\n[ERROR] Failed to run shopify CLI: {e}")

if __name__ == "__main__":
    main()
