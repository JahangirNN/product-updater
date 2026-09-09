# ADR 0003: Declarative Configuration-Driven Architecture

## Status
Accepted

## Date
2026-09-09

## Context
Previously, update intervals, crawl depth, site-specific endpoints, timeout parameters, and currency conversion logic were hardcoded across multiple Python script files. Changing the check frequency from 10 minutes to 30 minutes or altering a site's concurrency limit required editing source code directly, introducing operational risk and code drift.

## Decision
All operational parameters, schedules, site definitions, and updater rules must be defined declaratively in a central configuration file (`config/config.yaml`).

The configuration will govern:
1. **Schedules & Intervals**: Global update intervals (e.g. `10m`), discovery intervals (e.g. `24h`), and cron expressions.
2. **Site Profiles**: Concurrency limits, request delays, user agent pools, timeout thresholds, and preferred extraction mode.
3. **Storage Settings**: Database connection string, file snapshot paths, and retention policies.
4. **Alerts & Thresholds**: Price change alerts (e.g. notify if price drops > 15%), out-of-stock notification triggers.

The Python runtime will validate this file upon startup using Pydantic models to fail fast on invalid configurations.

## Consequences
- **Positive**:
  - Non-programmers or operations can tune schedules without touching code.
  - Zero downtime configuration changes.
  - Easy environment switching (e.g. development vs production schedules).
- **Negative**:
  - Requires maintaining a robust configuration schema and validation parser.
