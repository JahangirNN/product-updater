# ADR 0009: Centralized Structured Logging & Background Scheduler Daemon

## Status
Accepted

## Date
2026-09-10

## Context
As the product catalog expands (now 422+ products across multiple collections), the systematic delta freshner must run autonomously in the background on a 1-hour recurring schedule. However:
1. Standard Python `print()` statements are insufficient for unattended background processes: they do not provide automatic file rotation, timestamp retention, or thread-safe queuing.
2. In production, runtime anomalies (e.g. retailer HTTP 429 rate limiting, 5xx server errors, network connection dropouts, malformed payload changes) must be immediately distinguishable from routine status logging. Burying errors inside millions of lines of polling events impairs forensic triaging.
3. The catalog freshner must support continuous background execution while remaining responsive to shutdown signals (SIGINT, SIGTERM) and cleanly reporting cycle execution metrics.
4. All new modules must strictly preserve the pure functional architecture (ADR 0005) with zero OOP classes.

## Decision
1. **Loguru-Powered Functional Logging**:
   - Selected `loguru` (following web research and Context7 best practice analysis) for its zero-boilerplate diagnostics, asynchronous non-blocking thread safety (`enqueue=True`), and native multi-sink routing.
   - Encapsulated all logging operations inside a pure functional module [`storage/logger.py`](file:///storage/logger.py) with graceful standard library fallback.
2. **Dual-Sink Log Placement & Error Isolation**:
   - **General Operational Log** (`logs/freshner.log`): Captures all `INFO`+ events with timestamp and module line, rotated at 20 MB, retained for 14 days.
   - **Error Diagnostic Log** (`logs/errors.log`): Strictly isolates `ERROR` and `CRITICAL` events with full diagnostic stack traces and variable states (`backtrace=True`, `diagnose=True`), rotated at 10 MB, retained for 30 days.
   - **Console Sink**: Real-time terminal output with ANSI colorized level tags for developer clarity.
3. **1-Hour Scheduling Configuration**:
   - Updated `check_interval_minutes: 60` in `config/delta_config.json` for both global defaults and per-store profiles.
4. **Persistent Background Scheduler Daemon**:
   - Implemented [`scripts/run_freshner_daemon.py`](file:///scripts/run_freshner_daemon.py) which executes `run_catalog_sync()` continuously.
   - Computes dynamic sleep intervals (`(interval * 60) - cycle_duration`) and sleeps with a 1-second heartbeat to allow immediate, graceful termination upon receiving OS signals.
   - Supports `--once` for ad-hoc validation and `--interval` for operational customization.

## Consequences
- **Positive**: Complete forensic isolation of errors in `logs/errors.log`; unattended operation without risk of disk exhaustion; clean separation between operational logs and the Shopify delta queue.
- **Negative**: Adds `loguru` as a dependency (mitigated by functional fallback to Python `logging`).
