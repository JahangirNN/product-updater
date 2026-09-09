# Configuration Specification (`config.yaml`)

## 1. Overview

The Product Updater runtime is controlled by a unified configuration file (`config/config.yaml`). The configuration is parsed and validated at application startup using Pydantic schema models.

---

## 2. Complete Reference Schema

```yaml
# ==============================================================================
# PRODUCT UPDATER: CORE RUNTIME CONFIGURATION
# ==============================================================================

version: "1.0"
environment: "development" # "development" | "production" | "staging"

# ------------------------------------------------------------------------------
# 1. SCHEDULER & INTERVAL DEFINITIONS
# ------------------------------------------------------------------------------
scheduler:
  # Frequency at which existing products are polled for price and stock changes
  price_stock_interval_minutes: 10
  
  # Frequency at which Firecrawl runs discovery on registered brand/category URLs
  discovery_interval_hours: 24
  
  # Max concurrent workers for the delta updater
  max_concurrent_workers: 4
  
  # Maximum items per delta batch
  batch_size: 50
  
  # Jitter to avoid predictable polling patterns (seconds)
  jitter_seconds: 5

# ------------------------------------------------------------------------------
# 2. FIRECRAWL INGESTION SETTINGS
# ------------------------------------------------------------------------------
firecrawl:
  api_key_env: "FIRECRAWL_API_KEY" # Reads from environment variable or .env
  base_url: "https://api.firecrawl.dev/v1"
  mcp_url: "https://mcp.firecrawl.dev/v2/mcp"
  timeout_seconds: 60
  max_retries: 3
  extract_schema: "canonical_product_v1" # Schema profile for extraction

# ------------------------------------------------------------------------------
# 3. STORAGE ROOM (MANAGED DATABASE & FILES)
# ------------------------------------------------------------------------------
storage:
  driver: "sqlite" # "sqlite" | "postgresql"
  sqlite:
    database_path: "storage/product_updater.db"
  postgresql:
    connection_uri_env: "DATABASE_URL"
  exports:
    enabled: true
    static_json_path: "storage/exports/products_latest.json"
    backup_directory: "storage/backups"

# ------------------------------------------------------------------------------
# 4. RETAILER PROFILES & TARGET RULES
# ------------------------------------------------------------------------------
retailers:
  # Example site profile template
  site_template:
    enabled: true
    currency: "INR"
    delta_strategy: "http_json" # "http_json" | "crawlee" | "playwright"
    request_delay_seconds: 1.5
    headers:
      User-Agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    selectors:
      price_container: ""
      stock_indicator: ""
    thresholds:
      price_drop_alert_pct: 15.0
      delist_on_404: false # Delist product if source returns HTTP 404

# ------------------------------------------------------------------------------
# 5. LOGGING & TELEMETRY
# ------------------------------------------------------------------------------
logging:
  level: "INFO" # "DEBUG" | "INFO" | "WARNING" | "ERROR"
  format: "structured_json" # "structured_json" | "human_readable"
  file_path: "logs/product_updater.log"
  max_size_mb: 50
  backup_count: 5
```
