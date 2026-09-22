# ADR 0017: Zero-Token Local Camoufox Stealth Browser Akamai Solver, DOM-Level React Hydration Sync, and Cooldown Resilience

## Status
Accepted

## Date
2026-09-22

## Context

1. **Zero-Token Mandate for Recurring Delta Freshness**:
   While external scraping APIs (e.g. Firecrawl) provide convenient ingress for one-time bulk catalog ingestion, recurring background delta sweeps running every 60 minutes across thousands of products must operate with **$0.00 external API cost and 0 token consumption**.

2. **Akamai Bot Manager Challenge on JD Sports**:
   Direct unauthenticated HTTP clients (`httpx`, `curl`) sent to JD Sports (`jdsports.com`) PDPs trigger Akamai Bot Manager, returning HTTP 403 Forbidden with JavaScript telemetry challenge scripts (`/21bC_d/...`). Unauthenticated HTTP sweeps cannot retrieve hydrated product inventory or prices.

3. **React/Next.js Client-Side Hydration Dynamics**:
   JD Sports PDPs serve an initial static HTML payload containing basic breadcrumbs (`BreadcrumbList`), but stream the detailed `ProductGroup` JSON-LD and granular variant inventory client-side via Next.js React Server Components (RSC) and React hydration. Simple string matching on raw HTML strings can prematurely evaluate static scripts before dynamic variant schemas are rendered.

4. **Temporary IP-Level Cooldowns & Throttling**:
   Rapid bursts of headless browser navigations without sufficient pacing can trigger Akamai's temporary 15-minute IP rate limit (`Your Access Has Been Denied... Please check back in 15 minutes`). The engine must intercept these early, trip the circuit breaker cleanly, and enforce polite pacing.

---

## Decision

1. **Local Stealth Headless Browser Solver (`stores/jdsports/camoufox_solver.py`)**:
   Implement a dedicated local solver using Camoufox (stealth Firefox fork with anti-fingerprinting patches) to execute Akamai JavaScript challenges locally on the host machine with zero external API calls or proxy costs.

2. **Aggressive Route Blocking for 3–5x Speedup**:
   Attach route filtering (`setup_camoufox_route_blocking`) to intercept and abort requests for heavy media, images, video, web fonts, and third-party tracking/analytics domains (`doubleclick`, `quantummetric`, `branch.io`, `criteo`, `hotjar`, etc.), while permitting primary scripts and document streams necessary for Akamai challenge resolution and React hydration.

3. **Route Handler Idempotency Guard**:
   Protect page route filter attachments against duplicate registration during long-running browser recycling using an explicit guard attribute (`getattr(page, "_route_blocking_active", False)`).

4. **Live DOM-Level Evaluation (`page.evaluate`)**:
   Poll for the client-side injected `ProductGroup` schema directly within the live browser DOM using `document.querySelectorAll('script[type="application/ld+json"]')` inside `page.evaluate(...)` rather than parsing static server HTML strings.

5. **Early HTTP 403 / 429 Status Interception**:
   Inspect `resp.status` immediately upon navigation. If HTTP 403 or 429 is encountered, immediately return `status: "rate_limited"` without waiting for DOM hydration timeouts, allowing `sync_catalog.py` to trip the circuit breaker (`trip_circuit_breaker`) and pause polling until the temporary cooldown clears.

6. **Polite Pacing Configuration (`config/delta_config.json`)**:
   Configure `jdsports` with `"engine": "camoufox"`, `"max_workers": 1`, `"requests_per_second": 0.33`, and `"delay_seconds": 3.0` to ensure smooth, polite execution below Akamai's rate-limiting thresholds.

7. **Parent-Child Stock Harmony & Tri-Field Currency Integrity (ADR 0006, ADR 0015)**:
   Maintain whole-rupee INR pricing with zero decimal paise, accurate US/UK/EU sizing tokens, and parent stock derivation (`in_stock` iff any variant is available).

---

## Consequences

- **Positive**:
  - **Zero Cost & Zero Tokens**: Delta sweeps for JD Sports run completely locally on the host machine with **$0.00 API expenses**.
  - **High Performance**: Route blocking reduces per-product sweep latency to ~5–7 seconds.
  - **Full Sizing Matrix Accuracy**: Live DOM extraction retrieves 100% of variant SKUs, US sizes, prices, and stock statuses across all colorways.
  - **Multi-Store Isolation**: When JD Sports enters an Akamai cooldown, only JD Sports pauses while Foot Locker, JW PEI, Coach, Michael Kors, and Nordstrom proceed without interruption.
- **Negative / Trade-offs**:
  - Headless browser execution requires local memory and CPU resources compared to raw HTTP requests. Handled via periodic page recycling every 25 items.
