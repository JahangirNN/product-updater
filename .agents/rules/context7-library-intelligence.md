# Rule: Mandatory Library Intelligence via Context7

## 1. Directive
Whenever writing, refactoring, or integrating third-party libraries (including, but not limited to: `pydantic`, `crawlee`, `playwright`, `httpx`, `pyyaml`, `firecrawl-py`, `requests`, or Shopify API clients), the agent **MUST** consult **Context7** to fetch authoritative, version-accurate documentation, current method signatures, and official best practices before implementing code.

Never guess method names, deprecated options, or obsolete syntax.

---

## 2. Where Context7 Shines
- **Zero Hallucinations on Modern APIs**: Libraries like Pydantic (v1 vs v2 migrations), Crawlee for Python, and modern Playwright have rapidly evolving interfaces. Context7 provides real-time, official documentation straight from authoritative repositories.
- **Idiomatic Best Practices**: Injects official architectural patterns (e.g. async context managers, connection pooling, backoff decorators, typed validation).
- **Exact Syntax & Type Annotations**: Verifies exact parameter types and return schemas before writing code.

---

## 3. Required Execution Protocol
Before generating code that uses an external library:

1. **Step 1: Resolve Library ID**
   - Call Context7 MCP tool `resolve-library-id` with the library name (e.g. `libraryName: "pydantic"` or `libraryName: "crawlee"`).
2. **Step 2: Fetch Documentation & Examples**
   - Call `get-library-docs` using the resolved library ID, focusing on the specific modules, classes, or functions needed for the task.
3. **Step 3: Implement According to Retrieved Docs**
   - Write code that strictly matches the official patterns retrieved from Context7.
   - Maintain pure functional style (no class bloat, per ADR 0005).
