"""
Catalog Pricing Research Shortcut (scripts/research_pricing.py)
Direct entrypoint for Step 1 of the Price Attack workflow.
Analyzes empirical USD pricing distributions, quantiles, and variant price spreads.
"""
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from scripts.resync_storefront_prices import main

if __name__ == "__main__":
    if "--research" not in sys.argv and "--simulate" not in sys.argv and "--dry-run" not in sys.argv and "--execute" not in sys.argv:
        sys.argv.insert(1, "--research")
    main()
