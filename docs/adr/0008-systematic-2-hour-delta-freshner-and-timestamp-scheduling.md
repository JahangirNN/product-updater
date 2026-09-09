# ADR 0008: Systematic 2-Hour Delta Freshner & Timestamp-Based Scheduling

## Status
Accepted

## Date
2026-09-10

## Context
Monitoring product price and stock availability requires continuous, systematic execution across expanding retailer catalogs. However:
1. Running blind full-catalog sweeps on every execution triggers unnecessary HTTP requests, wastes bandwidth, and risks CDN rate limiting (HTTP 429).
2. Different retailers require different concurrency, request timeouts, and polite delay parameters.
3. Operators need to configure checking intervals easily (e.g. standard 2-hour window vs 2-minute testing intervals) without altering Python source code.
4. When price or stock shifts are detected, the system must atomically persist changes to disk, recalculate whole-rupee INR pricing using cached forex rates, and queue structured events for future Shopify Admin API synchronization.

## Decision
1. **Centralized Configuration**:
   - Created `config/delta_config.json` defining default check intervals (`check_interval_minutes: 120`), polite concurrency (`max_workers: 3`, `delay_seconds: 0.08`), and per-store configuration blocks.
2. **Product-Level Timestamp Check**:
   - Every product document tracks `last_verified_at` (ISO 8601 UTC timestamp).
   - The checker evaluates `elapsed = (now - last_verified_at) / 60.0`. Only products where `elapsed >= interval_minutes` are polled.
   - Touching `last_verified_at` upon every check ensures verified products are automatically skipped in subsequent runs until the 2-hour window expires.
   - A `--force` CLI flag is provided to bypass timestamp filtering for on-demand auditing.
3. **Universal Multi-Store Dispatcher**:
   - Created `sync_catalog.py` as a unified global orchestrator that dynamically imports `stores/{store}/delta.py`.
4. **Delta Persistence & Shopify Queueing**:
   - When price changes: updates USD source price, recalculates whole-rupee INR price (`current_price`), and updates variant prices.
   - When stock changes: flips availability (`in_stock` $\leftrightarrow$ `out_of_stock`), updates variant availability, and sets `is_active`.
   - On change, sets `shopify_sync_pending = True` in the product JSON and appends a structured event to `storage/db/history/delta_events.json`.
   - Execution batch metrics are appended to `storage/db/history/delta_log.json`.
5. **Pure Functional Architecture**:
   - All modules (`sync_catalog.py`, `stores/jwpei/delta.py`, `storage/db.py`, `test_delta_engine.py`) consist strictly of pure functions (`def ...`) with zero classes, adhering to ADR 0005.

## Consequences
- **Positive**: If the updater is invoked frequently, only expired products are polled. 100% fresh catalogs consume 0 network requests and complete in <0.1 seconds.
- **Negative**: Requires accurate system time (UTC) for reliable timestamp delta calculations.
