# Rule: Live Research First Protocol (Context7 & Google Search Grounding)

## 1. Directive
Whenever interacting with, configuring, or implementing code for external SaaS platforms (e.g., Shopify, Cloudflare, AWS), third-party APIs, authentication systems (OAuth 2.0, API keys, CLI auth), or fast-moving software libraries, **NEVER rely on static or historical training memory alone**.

External platforms and developer tools continuously deprecate legacy flows and release new versions. Always ground actions with **Context7 MCP** for library APIs and **Live Web Search (Google)** for platform workflows, CLI commands, and error diagnostics.

---

## 2. Mandatory Dual-Grounding Protocol

### 2.1 For Code Libraries & SDK Frameworks (Context7 First)
- Before implementing features with modern libraries (e.g., `httpx`, `curl_cffi`, `pydantic`, `vite`, `tailwindcss`, `playwright`, `loguru`):
  1. Call `context7` MCP (`resolve-library-id` -> `query-docs`).
  2. Inspect official up-to-date documentation, version changes, and recommended API patterns.

### 2.2 For Platform UI, CLI Commands & SaaS Workflows (Google Search First)
- Before guiding users through platform dashboards (e.g., Shopify Dev Dashboard, Shopify Admin, Google Cloud, Cloudflare) or running CLI tooling:
  1. Use `search_web` with current year/date scoping (e.g., `Shopify "theme dev" CLI 2026`).
  2. Ground instructions in current UI layout, button labels, and authentication methods.

### 2.3 Immediate Search on External Error Codes & API Anomalies
- The instant an external service returns an unexpected status (e.g., `401 Unauthorized`, `493 Bot Protection`, `application_cannot_be_found`, `EPIPE`):
  - **Do NOT speculate or guess based on old workflows.**
  - Immediately execute `search_web` targeting the exact error phrase and service name to discover the precise cause and official fix.

---

## 3. Invariants
- **No Stale Assumptions**: Never assume legacy dashboard layouts, token generation buttons, or CLI flag syntax remain unchanged.
- **Verification Before Recommendation**: Search first -> verify exact mechanics -> propose solution.
