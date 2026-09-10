# Structured Logging Specification & Error Isolation Architecture

This document defines the centralized logging architecture, error isolation sinks, log rotation and retention policies, and monitoring runbooks for the `product-updater` catalog freshness engine.

---

## 1. Core Objectives

1. **High Developer Visibility**: Provide clean, color-coded console logs during active executions with immediate identification of log levels (`INFO`, `WARNING`, `SUCCESS`, `ERROR`, `CRITICAL`).
2. **Dedicated Error Isolation**: Separate operational metrics from runtime anomalies so developers and operators can triage failures instantly without filtering through millions of lines of routine polling events.
3. **Thread-Safe Asynchronous Sinks**: Support concurrent multi-worker delta polling without I/O contention or corrupted log lines via non-blocking queued sinks (`enqueue=True`).
4. **Automated Log Lifecycle Management**: Prevent disk exhaustion on unattended background runners via size-based rotation and time-based retention.
5. **Pure Functional Architecture**: Fully comply with [ADR 0005](file:///docs/adr/0005-functional-screaming-architecture-and-store-knowledge-bases.md) with zero OOP classes or logger instance inheritance.

---

## 2. Directory Layout & Routing

All runtime log files are placed in the top-level `logs/` directory, which is gitignored to protect sensitive operational traces:

```
product-updater/
├── logs/
│   ├── freshner.log     # General operational log (INFO, WARNING, SUCCESS, ERROR)
│   └── errors.log       # Isolated error forensic log (ERROR, CRITICAL only with diagnostics)
├── storage/
│   └── logger.py        # Centralized functional logging module
├── scripts/
│   └── run_freshner_daemon.py  # 1-hour background scheduler daemon
└── config/
    └── delta_config.json       # Centralized intervals and logging configurations
```

---

## 3. Dual-Sink Routing & Policy Matrix

| Sink Target | Minimum Level | Format & Features | Rotation Policy | Retention Policy | Purpose |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Console (`sys.stdout`)** | `INFO` | ANSI Colorized: `<green>timestamp</green> \| <level>LEVEL</level> \| module:line - message` | N/A (terminal stream) | N/A | Real-time terminal feedback for manual and daemon execution. |
| **`logs/freshner.log`** | `INFO` | `YYYY-MM-DD HH:mm:ss.SSS \| LEVEL    \| module:line - message` | **20 MB** (or daily) | **14 days** | Complete historical record of polling cycles, product statuses, and price/stock deltas. |
| **`logs/errors.log`** | `ERROR` | `YYYY-MM-DD HH:mm:ss.SSS \| ERROR    \| module:line - message` + `backtrace=True`, `diagnose=True` | **10 MB** | **30 days** | **High-priority error forensic log**. Isolates connection timeouts, HTTP 429/500 errors, JSON decode failures, and disk write errors with variables and stack trace. |

---

## 4. Delta Event & Shift Highlighting

When the delta engine detects an alteration in a retailer's live product state (e.g. price change or stock exhaustion), the event is highlighted with a dedicated prefix across both console and `logs/freshner.log`:

```
2026-09-10 10:41:35.120 | INFO     | sync_catalog:321 - [DELTA:PRICE] thea-top-handle-bag-almond -> $119.0 -> $99.0 USD
2026-09-10 10:41:35.125 | INFO     | sync_catalog:325 - [DELTA:STOCK] thea-large-top-handle-bag-black -> in_stock -> out_of_stock
```

Simultaneously, the structured event payload is persisted atomically to `storage/db/history/delta_events.json` for subsequent Shopify sync processing.

---

## 5. Configuration Schema (`config/delta_config.json`)

All logging parameters are declaratively managed in `config/delta_config.json`:

```json
{
  "check_interval_minutes": 60,
  "default_max_workers": 3,
  "default_delay_seconds": 0.08,
  "default_timeout_seconds": 6.0,
  "logging": {
    "log_dir": "logs",
    "general_log": "freshner.log",
    "error_log": "errors.log",
    "rotation_general": "20 MB",
    "rotation_error": "10 MB",
    "retention_general": "14 days",
    "retention_error": "30 days",
    "console_level": "INFO"
  }
}
```

---

## 6. Background Daemon Architecture

The background scheduler daemon (`scripts/run_freshner_daemon.py`) executes persistent monitoring cycles:

```
[Start Daemon] ──> Read delta_config.json (60 min)
       │
       ▼
[Cycle #N] ─────> Execute run_catalog_sync()
       │             ├── Scan storage/db/index.json
       │             ├── Skip products verified within 60 mins
       │             ├── Concurrently poll expired products
       │             └── Persist deltas & log summary
       │
       ▼
[Log Result] ───> Write cycle summary to logs/freshner.log
       │          (If errors occurred, write full traces to logs/errors.log)
       │
       ▼
[Sleep Calc] ───> target_sleep = (interval * 60) - cycle_duration
       │
       ▼
[Heartbeat] ────> Sleep in 1-second increments (responsive to SIGINT/SIGTERM)
       │
       └────────> Loop to Cycle #N+1
```

---

## 7. Operator Runbook & Monitoring Commands

### Inspect Active Errors
To view isolated errors and stack traces in real time:
```powershell
# PowerShell
Get-Content logs/errors.log -Tail 30 -Wait
```
```bash
# Unix/Git Bash
tail -f logs/errors.log
```

### Inspect General Polling Progress
To follow the live freshner daemon activity:
```powershell
# PowerShell
Get-Content logs/freshner.log -Tail 50 -Wait
```

### Run Single Cycle On-Demand
To perform a single sweep without entering the persistent loop:
```powershell
python scripts/run_freshner_daemon.py --once
```

### Start Background Monitoring Daemon
To start the daemon in the background:
```powershell
# Standard execution
python scripts/run_freshner_daemon.py

# Custom 30-minute interval override
python scripts/run_freshner_daemon.py --interval 30
```
