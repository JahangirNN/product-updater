"""
Documentation & Architecture Alignment Verifier.
Ensures that all project documentation, ADR sequence numbers, and store modules adhere to standards.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]  # product-updater root

REQUIRED_DOCS = [
    "docs/ARCHITECTURE.md",
    "docs/SHOPIFY_INTEGRATION_SPEC.md",
    "docs/JSON_STORAGE_SPEC.md",
    "docs/FOLDER_STRUCTURE.md",
    "docs/CODING_STANDARDS.md",
    "README.md",
]

def verify_docs():
    errors = []
    print(f">> Checking documentation integrity in: {ROOT}")

    # 1. Check Core Documentation Files
    for doc in REQUIRED_DOCS:
        doc_path = ROOT / doc
        if not doc_path.exists():
            errors.append(f"Missing core document: {doc}")
        else:
            print(f"  [OK] {doc}")

    # 2. Check ADR Sequence and Formats
    adr_dir = ROOT / "docs" / "adr"
    if not adr_dir.exists():
        errors.append("Missing docs/adr directory")
    else:
        adrs = sorted([f for f in adr_dir.glob("*.md")])
        expected_num = 1
        for adr in adrs:
            match = re.match(r"^(\d{4})-(.+)\.md$", adr.name)
            if not match:
                errors.append(f"Invalid ADR filename format: {adr.name} (must be NNNN-title.md)")
                continue
            num = int(match.group(1))
            if num != expected_num:
                errors.append(f"ADR sequence break: expected {expected_num:04d}, found {adr.name}")
            expected_num = num + 1

            # Check status header inside ADR
            content = adr.read_text(encoding="utf-8")
            if "## Status" not in content or "## Decision" not in content:
                errors.append(f"ADR {adr.name} missing '## Status' or '## Decision' section")
            else:
                print(f"  [OK] ADR {adr.name}")

    # 3. Check Store Modules
    stores_dir = ROOT / "stores"
    if stores_dir.exists():
        for store in stores_dir.iterdir():
            if store.is_dir() and not store.name.startswith("."):
                learnings = store / "LEARNINGS.md"
                inflow = store / "inflow.py"
                delta = store / "delta.py"

                if not learnings.exists():
                    errors.append(f"Store '{store.name}' is missing LEARNINGS.md")
                if not inflow.exists():
                    errors.append(f"Store '{store.name}' is missing inflow.py")
                if not delta.exists():
                    errors.append(f"Store '{store.name}' is missing delta.py")

                if learnings.exists() and inflow.exists() and delta.exists():
                    print(f"  [OK] Store module: {store.name}")

    print("\n---------------------------------------------------")
    if errors:
        print(f"FAILED: {len(errors)} documentation issue(s) detected:")
        for err in errors:
            print(f"  [!] {err}")
        sys.exit(1)
    else:
        print("SUCCESS: All architecture docs, ADRs, and store knowledge bases are 100% aligned!")
        sys.exit(0)

if __name__ == "__main__":
    verify_docs()
