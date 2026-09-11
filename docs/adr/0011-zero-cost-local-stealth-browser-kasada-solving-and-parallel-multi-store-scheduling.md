# ADR 0011: Zero-Cost Local Stealth Browser Kasada Solving & Parallel Multi-Store Delta Scheduling

## Status
Accepted

## Date
2026-09-11

## Context
As the dropship catalog expanded to include Nordstrom footwear, two major technical challenges arose:
1. **Kasada Bot Protection & Cost Constraints**: Nordstrom protects its storefront with Kasada JavaScript client-side proof-of-work challenges (`window['istlWas']`). Standard HTTP and TLS impersonation clients (`httpx`, `curl_cffi`) are intercepted with empty challenge screens. Relying on commercial scraper APIs (e.g. Firecrawl) for continuous hourly delta sweeps would introduce unsustainable recurring operational costs ($100s/month).
2. **Granular Multi-Size Footwear Inventory**: Shoe models possess 10–16 distinct size variants. Standard page-level availability checks (`in_stock` vs `out_of_stock`) fail to capture individual size stockouts (e.g., US 7 sold out while US 7.5 remains in stock), leading to false availability signals on storefronts.
3. **Multi-Store Scheduling Contention**: Different retailer storefronts have fundamentally different latency and rendering characteristics. Fast HTTP stores (JW PEI @ ~400ms) would be severely bottlenecked if serialized behind browser-rendered stores (Nordstrom @ ~7s).

## Decision

1. **Local Stealth Browser Engine ([`stores/nordstrom/camoufox_solver.py`](../../stores/nordstrom/camoufox_solver.py))**:
   - Integrated `camoufox` (open-source C++ stealth Firefox fork) paired with `playwright` to execute Kasada's JavaScript proof-of-work locally for $0.00 external cost.
   - Built pure functional lifecycle management (`create_nordstrom_browser_session()`, `close_nordstrom_browser_session()`) with zero OOP classes (ADR 0005).
   - Solves the challenge in ~4–6 seconds per PDP. Used `page.wait_for_timeout()` instead of `time.sleep()` to prevent freezing the Playwright event pump.
   - Strict anti-false-positive guardrail: Never mask blocked challenge pages as success; if `istlWas` remains unresolved, report `status: "blocked"`.

2. **Granular Per-Size Inventory Extraction**:
   - Decoded Nordstrom's dehydrated `window.__INITIAL_CONFIG__` entity tree (~420KB JSON) via `json.JSONDecoder().raw_decode()`.
   - Traversed `coreChoices` -> `items` -> `propositions[0].availability.shipQuantity` to retrieve exact per-size live inventory.
   - Mapped sizes to canonical variants (`var["in_stock"] = (shipQuantity > 0)`).
   - In [`stores/nordstrom/delta.py`](../../stores/nordstrom/delta.py), set `variant_stock_changed = True` if any individual size stock status flips, flagging `has_changed = True` and queueing the event in `storage/db/history/delta_events.json` for Shopify sync.

3. **Parallel Multi-Store Delta Orchestration ([`sync_catalog.py`](../../sync_catalog.py))**:
   - Grouped due products by store and spawned dedicated store workers concurrently via `ThreadPoolExecutor(max_workers=len(by_store))`.
   - Fast HTTP stores (JW PEI) process hundreds of products in 2–3 minutes via their own worker pool, while browser stores (Nordstrom) run in parallel without cross-store blocking.

## Consequences

- **Positive**:
  - **Zero Scraper API Cost**: Completely autonomous local Kasada solving without recurring API subscriptions.
  - **Accurate Size Inventory**: Individual shoe size stockouts and restocks are detected and persisted atomically.
  - **High Throughput**: Multi-store parallel execution isolates store latencies and preserves system responsiveness.
  - **Data Integrity**: Preserves atomic writing (`.tmp` + `os.replace`) and strict selective timestamp stamping.
- **Negative**:
  - Headless browser rendering consumes more CPU/RAM than raw HTTP calls; Nordstrom worker concurrency is appropriately capped at 1 worker with polite delays (1.5s).
