#!/usr/bin/env python3
"""
Deploy The Rare Avenue Quiet Luxury Storefront to Licensed Horizon Theme
Target Theme: gid://shopify/OnlineStoreTheme/198751387814 (Horizon v4.3.0, themeStoreId: 2481)
Adheres strictly to ADR 0005, ADR 0022, ADR 0029, ADR 0030, GEMINI.md, and PROJECT.md.

Enforces:
1. Pure Client Credentials GraphQL execution via storage.shopify_auth.execute_shopify_graphql
2. Pre-deployment anti-copyright gate (0 Maestrooo/Prestige occurrences)
3. Correct payload typing: TEXT for liquid/json/css/js/svg, BASE64 for PNG
4. Post-deployment readback verification
"""
import os
import sys
import base64
import json
import re
import time
from typing import List, Dict, Any, Tuple

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql
from storage.logger import log_info, log_success, log_warning, log_error

THEME_ID = "gid://shopify/OnlineStoreTheme/198751387814"
THEME_DIR = os.path.join(PROJECT_ROOT, "horizon_clean_theme")

THEME_FILES_UPSERT_MUTATION = """
mutation themeFilesUpsert($themeId: ID!, $files: [OnlineStoreThemeFilesUpsertFileInput!]!) {
  themeFilesUpsert(themeId: $themeId, files: $files) {
    upsertedThemeFiles {
      filename
      size
      checksumMd5
      updatedAt
    }
    userErrors {
      code
      field
      filename
      message
    }
  }
}
"""

THEME_FILES_READBACK_QUERY = """
query getThemeFiles($themeId: ID!, $filenames: [String!]!) {
  theme(id: $themeId) {
    id
    name
    themeStoreId
    files(filenames: $filenames) {
      nodes {
        filename
        size
        updatedAt
      }
    }
  }
}
"""

BANNED_PATTERNS = [
    r'maestrooo',
    r'<loading-bar',
    r'</loading-bar',
    r'<mega-menu-disclosure',
    r'</mega-menu-disclosure',
    r'<facet-link',
    r'</facet-link',
    r'<accordion-disclosure',
    r'</accordion-disclosure',
    r'support\.maestrooo\.com',
    r'theme\.js\b',
    r'theme\.css\b'
]


def pre_deployment_audit() -> List[str]:
    """Scans all files in THEME_DIR against clean-room invariants."""
    log_info("Executing Pre-Deployment Anti-Copyright Clean-Room Audit...")
    violations = []
    file_count = 0
    for root, _, files in os.walk(THEME_DIR):
        for file in files:
            fpath = os.path.join(root, file)
            rel_path = os.path.relpath(fpath, THEME_DIR).replace("\\", "/")
            if file.endswith(('.liquid', '.json', '.js', '.css', '.svg', '.html')):
                file_count += 1
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                for pat in BANNED_PATTERNS:
                    matches = re.findall(pat, content, re.I)
                    if matches:
                        violations.append(f"{rel_path}: matches banned pattern '{pat}' ({len(matches)} times)")
    if violations:
        log_error(f"Pre-deployment audit failed with {len(violations)} violations!")
        for v in violations:
            log_error(f"  - {v}")
        raise ValueError("Deployment aborted due to clean-room copyright violations.")
    log_success(f"Audit passed: {file_count} text files scanned, 0 copyright violations detected.")
    return violations


def build_deployment_payload() -> List[Dict[str, Any]]:
    """Builds typed payload for themeFilesUpsert mutation."""
    files_payload = []
    for root, _, files in os.walk(THEME_DIR):
        for file in files:
            fpath = os.path.join(root, file)
            rel_name = os.path.relpath(fpath, THEME_DIR).replace("\\", "/")
            ext = os.path.splitext(file)[1].lower()

            if ext in ['.liquid', '.json', '.js', '.css', '.svg', '.html']:
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
                files_payload.append({
                    "filename": rel_name,
                    "body": {
                        "type": "TEXT",
                        "value": content
                    }
                })
            elif ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.ico']:
                with open(fpath, 'rb') as f:
                    b64_content = base64.b64encode(f.read()).decode('utf-8')
                files_payload.append({
                    "filename": rel_name,
                    "body": {
                        "type": "BASE64",
                        "value": b64_content
                    }
                })
            else:
                log_warning(f"Skipping unhandled file type: {rel_name}")
    return files_payload


def deploy_batch(files_chunk: List[Dict[str, Any]]) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Deploys a chunk of files using themeFilesUpsert."""
    res, raw, status = execute_shopify_graphql(
        THEME_FILES_UPSERT_MUTATION,
        variables={
            "themeId": THEME_ID,
            "files": files_chunk
        }
    )
    if not res or "themeFilesUpsert" not in res:
        err_msg = raw if raw else "Empty response from Shopify GraphQL"
        raise RuntimeError(f"GraphQL error during themeFilesUpsert: {err_msg}")

    data = res["themeFilesUpsert"]
    upserted = [f["filename"] for f in data.get("upsertedThemeFiles", [])]
    user_errors = data.get("userErrors", [])
    return upserted, user_errors


def verify_deployment(filenames: List[str]) -> bool:
    """Verifies all files exist and are populated on the remote theme via readback."""
    log_info(f"Verifying {len(filenames)} files on remote theme via GraphQL readback...")
    
    # Query in batches of 50 to avoid GraphQL complexity limits
    batch_size = 50
    missing = []
    verified_count = 0
    
    for i in range(0, len(filenames), batch_size):
        chunk = filenames[i:i + batch_size]
        res, _, _ = execute_shopify_graphql(
            THEME_FILES_READBACK_QUERY,
            variables={"themeId": THEME_ID, "filenames": chunk}
        )
        if not res or "theme" not in res or "files" not in res["theme"]:
            log_error(f"Readback query failed for batch {i // batch_size + 1}")
            return False
            
        nodes = res["theme"]["files"].get("nodes", [])
        found_names = {n["filename"]: n["size"] for n in nodes if n.get("size") is not None}
        
        for name in chunk:
            if name in found_names:
                verified_count += 1
            else:
                missing.append(name)
                
    if missing:
        log_error(f"Readback verification failed! {len(missing)} files missing on remote theme: {missing}")
        return False
        
    log_success(f"Readback verified: All {verified_count} files confirmed live on {THEME_ID}!")
    return True


def run_deployment():
    """Main deployment pipeline."""
    log_info("=" * 70)
    log_info("STARTING THE RARE AVENUE QUIET LUXURY HORIZON THEME DEPLOYMENT")
    log_info(f"Target Theme: {THEME_ID}")
    log_info("=" * 70)

    # 1. Pre-deployment copyright scan
    pre_deployment_audit()

    # 2. Build payload
    payload = build_deployment_payload()
    log_info(f"Prepared {len(payload)} theme files for deployment.")

    # 3. Deploy in batches of 10 files
    chunk_size = 8
    all_upserted = []
    all_errors = []

    for i in range(0, len(payload), chunk_size):
        chunk = payload[i:i + chunk_size]
        chunk_names = [f["filename"] for f in chunk]
        log_info(f"Deploying batch {i // chunk_size + 1}/{(len(payload) + chunk_size - 1) // chunk_size} ({len(chunk)} files)...")
        upserted, errors = deploy_batch(chunk)
        all_upserted.extend(upserted)
        if errors:
            all_errors.extend(errors)
            for err in errors:
                log_error(f"  Error on {err.get('filename')}: {err.get('message')}")
        else:
            log_success(f"  Batch {i // chunk_size + 1} deployed: {upserted}")
        time.sleep(0.5)

    if all_errors:
        log_error(f"Deployment completed with {len(all_errors)} errors!")
        sys.exit(1)

    log_success(f"Successfully upserted {len(all_upserted)} theme files to {THEME_ID}!")

    # 4. Verify deployment
    filenames_to_verify = [f["filename"] for f in payload]
    success = verify_deployment(filenames_to_verify)
    if not success:
        sys.exit(1)

    log_info("=" * 70)
    log_success("THE RARE AVENUE HORIZON QUIET LUXURY DEPLOYMENT COMPLETE & VERIFIED!")
    log_info("=" * 70)


if __name__ == "__main__":
    run_deployment()
