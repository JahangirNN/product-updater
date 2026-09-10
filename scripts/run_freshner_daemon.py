"""
Continuous Background Freshner Daemon
Runs the systematic catalog delta sync on a configurable recurring schedule (default 60 minutes).
Provides responsive signal handling, detailed cycle logging, and isolated error tracking.
Pure functions only, zero classes (ADR 0005, ADR 0008, ADR 0009).
"""
import os
import sys
import time
import signal
import argparse
import datetime
from typing import Optional

# Ensure project root is on sys.path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from sync_catalog import run_catalog_sync, load_delta_config, DEFAULT_CONFIG_PATH
from storage.logger import (
    init_logger,
    log_info,
    log_success,
    log_warning,
    log_error,
    log_critical
)

_SHUTDOWN_REQUESTED = False


def register_signal_handlers() -> None:
    """Register graceful termination handlers for SIGINT and SIGTERM."""
    def _signal_handler(sig, frame):
        global _SHUTDOWN_REQUESTED
        sig_name = signal.Signals(sig).name if hasattr(signal, "Signals") else str(sig)
        log_info(f"Received signal {sig_name}. Initiating graceful shutdown...")
        _SHUTDOWN_REQUESTED = True

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)


def sleep_with_heartbeat(seconds: float) -> None:
    """Sleep in small 1-second slices so shutdown signals are processed immediately."""
    end_time = time.time() + seconds
    while time.time() < end_time and not _SHUTDOWN_REQUESTED:
        time.sleep(min(1.0, end_time - time.time()))


def run_daemon_loop(
    interval_minutes: Optional[float] = None,
    store_filter: Optional[str] = None,
    force_first_cycle: bool = False,
    once: bool = False,
    config_path: str = DEFAULT_CONFIG_PATH
) -> None:
    """
    Main daemon loop executing run_catalog_sync() periodically.
    """
    global _SHUTDOWN_REQUESTED
    register_signal_handlers()

    config = load_delta_config(config_path)
    effective_interval = interval_minutes if interval_minutes is not None else config.get("check_interval_minutes", 60)

    log_info("=" * 72)
    log_info("DROPSHIP CATALOG BACKGROUND FRESHNER DAEMON STARTED")
    log_info("=" * 72)
    log_info(f"PID:                   {os.getpid()}")
    log_info(f"Schedule Interval:     {effective_interval:.1f} minutes ({effective_interval * 60:.0f} seconds)")
    log_info(f"Single Cycle Mode:     {once}")
    if store_filter:
        log_info(f"Store Filter:          {store_filter}")
    log_info(f"Operational Log:       logs/freshner.log")
    log_info(f"Error Diagnostic Log:  logs/errors.log")
    log_info("=" * 72)

    cycle_count = 1

    while not _SHUTDOWN_REQUESTED:
        cycle_start_time = time.time()
        log_info(f"\n>>> Starting Sync Cycle #{cycle_count} at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # In cycle 1, apply force_first_cycle if specified
        is_force = force_first_cycle if cycle_count == 1 else False

        try:
            results = run_catalog_sync(
                interval_override=effective_interval,
                store_filter=store_filter,
                force=is_force,
                config_path=config_path
            )

            scanned = results.get("scanned", 0)
            skipped = results.get("skipped", 0)
            p_shifts = results.get("price_changes", 0)
            s_shifts = results.get("stock_changes", 0)
            errs = results.get("errors", 0)

            log_success(
                f"Sync Cycle #{cycle_count} Completed | "
                f"Scanned: {scanned}, Skipped: {skipped}, "
                f"Price Shifts: {p_shifts}, Stock Shifts: {s_shifts}, "
                f"Errors: {errs}"
            )

        except Exception as exc:
            log_error(f"Unhandled exception during Sync Cycle #{cycle_count}", exc=exc)

        if once or _SHUTDOWN_REQUESTED:
            log_info(f"Exiting daemon loop ({'single-run --once completed' if once else 'shutdown requested'}).")
            break

        cycle_duration = time.time() - cycle_start_time
        target_sleep = max(10.0, (effective_interval * 60.0) - cycle_duration)
        next_wake = datetime.datetime.now() + datetime.timedelta(seconds=target_sleep)

        log_info(
            f"Cycle #{cycle_count} sweep took {cycle_duration:.1f}s. "
            f"Daemon sleeping for {target_sleep:.0f}s. "
            f"Next cycle #{cycle_count + 1} scheduled at {next_wake.strftime('%Y-%m-%d %H:%M:%S')}."
        )

        sleep_with_heartbeat(target_sleep)
        cycle_count += 1

    log_info("Background Freshner Daemon has stopped cleanly.")


def main():
    parser = argparse.ArgumentParser(description="Dropship Catalog Background Freshner Daemon")
    parser.add_argument(
        "--interval",
        type=float,
        help="Check interval in minutes (default reads from delta_config.json, e.g. 60 for 1 hour)"
    )
    parser.add_argument(
        "--store",
        type=str,
        help="Target specific store (e.g. jwpei)"
    )
    parser.add_argument(
        "--force-first",
        action="store_true",
        help="Force check all products on the first cycle regardless of last_verified_at"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single cycle and exit (useful for one-off testing)"
    )
    parser.add_argument(
        "--config",
        type=str,
        default=DEFAULT_CONFIG_PATH,
        help="Path to delta config JSON"
    )

    args = parser.parse_args()

    run_daemon_loop(
        interval_minutes=args.interval,
        store_filter=args.store,
        force_first_cycle=args.force_first,
        once=args.once,
        config_path=args.config
    )


if __name__ == "__main__":
    main()
