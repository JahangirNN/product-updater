"""
Centralized, Store-Agnostic Rate Limiter & Circuit Breaker
Thread-safe pacing, per-store sliding slot scheduling, and 429 circuit breaking.
Pure functions only, zero classes (ADR 0005, ADR 0010).
"""
import time
import threading
import email.utils
from typing import Any, Dict, Optional, Tuple, Union

_STORE_LOCKS: Dict[str, threading.Lock] = {}
_STORE_COOLDOWNS: Dict[str, float] = {}       # store -> epoch timestamp when cooldown ends
_NEXT_AVAILABLE_TS: Dict[str, float] = {}     # store -> epoch timestamp when next request can proceed
_STORE_CONFIGS: Dict[str, Dict[str, float]] = {}  # store -> {"requests_per_second": float, "delay_seconds": float}
_GLOBAL_LOCK = threading.Lock()

DEFAULT_REQUESTS_PER_SECOND = 2.0
DEFAULT_DELAY_SECONDS = 0.5
DEFAULT_COOLDOWN_SECONDS = 30.0
MAX_COOLDOWN_SECONDS = 300.0  # 5-minute safety cap against infinite lockout


def _get_store_lock(store_name: str) -> threading.Lock:
    """Retrieve or initialize a thread lock dedicated to a specific store."""
    clean_store = (store_name or "default").strip()
    with _GLOBAL_LOCK:
        if clean_store not in _STORE_LOCKS:
            _STORE_LOCKS[clean_store] = threading.Lock()
        return _STORE_LOCKS[clean_store]


def configure_store_rate_limits(
    store_name: str,
    requests_per_second: float = DEFAULT_REQUESTS_PER_SECOND,
    delay_seconds: float = DEFAULT_DELAY_SECONDS
) -> None:
    """
    Set rate limiting parameters for a store.
    Use store_name='default' to configure fallback limits.
    """
    store = (store_name or "default").strip()
    rps_val = DEFAULT_REQUESTS_PER_SECOND if requests_per_second is None else requests_per_second
    delay_val = DEFAULT_DELAY_SECONDS if delay_seconds is None else delay_seconds
    store_lock = _get_store_lock(store)
    with store_lock:
        _STORE_CONFIGS[store] = {
            "requests_per_second": max(0.01, float(rps_val)),
            "delay_seconds": max(0.0, float(delay_val))
        }


def get_store_rate_limits(store_name: str) -> Tuple[float, float]:
    """
    Get (requests_per_second, delay_seconds) for a store, falling back to default.
    """
    store = (store_name or "default").strip()
    store_lock = _get_store_lock(store)
    with store_lock:
        cfg = _STORE_CONFIGS.get(store)
        if not cfg:
            cfg = _STORE_CONFIGS.get("default", {
                "requests_per_second": DEFAULT_REQUESTS_PER_SECOND,
                "delay_seconds": DEFAULT_DELAY_SECONDS
            })
        return cfg.get("requests_per_second", DEFAULT_REQUESTS_PER_SECOND), cfg.get("delay_seconds", DEFAULT_DELAY_SECONDS)


def parse_retry_after(
    header_value: Optional[Union[str, int, float]],
    default_cooldown: float = DEFAULT_COOLDOWN_SECONDS
) -> float:
    """
    Parse Retry-After header value into seconds.
    Supports integer/float seconds and standard HTTP-date format (RFC 1123).
    Guards against None defaults and caps cooldown at MAX_COOLDOWN_SECONDS.
    """
    base_default = DEFAULT_COOLDOWN_SECONDS if default_cooldown is None else float(default_cooldown)
    if header_value is None:
        return min(MAX_COOLDOWN_SECONDS, max(1.0, base_default))
    val = str(header_value).strip()
    if not val:
        return min(MAX_COOLDOWN_SECONDS, max(1.0, base_default))

    # Attempt numeric parsing (seconds)
    try:
        sec = float(val)
        return min(MAX_COOLDOWN_SECONDS, max(1.0, sec))
    except ValueError:
        pass

    # Attempt HTTP date parsing
    try:
        parsed_tuple = email.utils.parsedate_tz(val)
        if parsed_tuple:
            target_ts = email.utils.mktime_tz(parsed_tuple)
            diff = target_ts - time.time()
            return min(MAX_COOLDOWN_SECONDS, max(1.0, diff))
    except Exception:
        pass

    return min(MAX_COOLDOWN_SECONDS, max(1.0, base_default))


def trip_circuit_breaker(
    store_name: str,
    cooldown_seconds: Optional[float] = DEFAULT_COOLDOWN_SECONDS
) -> float:
    """
    Trip the circuit breaker for a store after encountering HTTP 429.
    All sibling worker threads for this store will pause without thundering herds.
    Returns the epoch timestamp when cooldown will expire.
    """
    store = (store_name or "default").strip()
    actual_cooldown = DEFAULT_COOLDOWN_SECONDS if cooldown_seconds is None else float(cooldown_seconds)
    actual_cooldown = min(MAX_COOLDOWN_SECONDS, max(0.001, actual_cooldown))
    store_lock = _get_store_lock(store)
    with store_lock:
        now = time.time()
        expiry = now + actual_cooldown
        current = _STORE_COOLDOWNS.get(store, 0.0)
        new_cooldown = max(current, expiry)
        _STORE_COOLDOWNS[store] = new_cooldown

        # Advance next available slot so upcoming calls queue after cooldown
        current_next = _NEXT_AVAILABLE_TS.get(store, 0.0)
        _NEXT_AVAILABLE_TS[store] = max(current_next, new_cooldown)
        return new_cooldown


def create_store_limiter(store_name: str) -> Dict[str, Any]:
    """
    Pure functional closure-based per-store rate limiter and circuit breaker handle.
    Enables store-scoped permit acquisition and circuit tripping without global leakage.
    Zero classes (ADR 0005, ADR 0010).
    """
    store = (store_name or "default").strip()
    return {
        "store": store,
        "acquire_permit": lambda rps=None, delay=None: acquire_permit(store, rps, delay),
        "trip_circuit_breaker": lambda cooldown=DEFAULT_COOLDOWN_SECONDS: trip_circuit_breaker(store, cooldown),
        "is_circuit_open": lambda: is_circuit_open(store),
        "get_cooldown_remaining": lambda: get_cooldown_remaining(store),
        "configure": lambda rps=DEFAULT_REQUESTS_PER_SECOND, delay=DEFAULT_DELAY_SECONDS: configure_store_rate_limits(store, rps, delay),
        "get_limits": lambda: get_store_rate_limits(store)
    }


def is_circuit_open(store_name: str) -> bool:
    """
    Check if the circuit breaker for a store is currently open (cooling down).
    """
    store = (store_name or "default").strip()
    store_lock = _get_store_lock(store)
    with store_lock:
        return _STORE_COOLDOWNS.get(store, 0.0) > time.time()


def get_cooldown_remaining(store_name: str) -> float:
    """
    Get the remaining cooldown duration in seconds for a store (0.0 if not open).
    """
    store = (store_name or "default").strip()
    store_lock = _get_store_lock(store)
    with store_lock:
        remaining = _STORE_COOLDOWNS.get(store, 0.0) - time.time()
        return max(0.0, remaining)


def acquire_permit(
    store_name: str,
    requests_per_second: Optional[float] = None,
    delay_seconds: Optional[float] = None
) -> float:
    """
    Thread-safe permit acquisition for a store.
    Enforces per-store rate limits, spaces requests, and pauses cleanly
    when circuit breaker is tripped, preventing thundering herds.
    Returns the total seconds waited.
    """
    store = (store_name or "default").strip()
    rps_cfg, delay_cfg = get_store_rate_limits(store)
    rps = requests_per_second if requests_per_second is not None else rps_cfg
    delay = delay_seconds if delay_seconds is not None else delay_cfg

    min_interval = max(delay, 1.0 / rps if rps > 0 else 0.0)
    store_lock = _get_store_lock(store)
    total_waited = 0.0

    while True:
        with store_lock:
            now = time.time()
            cooldown_end = _STORE_COOLDOWNS.get(store, 0.0)

            # If cooldown active, schedule after cooldown expiration
            earliest_start = max(now, cooldown_end)
            prev_next = _NEXT_AVAILABLE_TS.get(store, 0.0)
            scheduled_slot = max(earliest_start, prev_next)
            _NEXT_AVAILABLE_TS[store] = scheduled_slot + min_interval

            sleep_duration = scheduled_slot - now

        if sleep_duration > 0:
            time.sleep(sleep_duration)
            total_waited += sleep_duration

            # Verify circuit breaker was not tripped during sleep
            with store_lock:
                cooldown_end = _STORE_COOLDOWNS.get(store, 0.0)
                if cooldown_end > time.time():
                    # Breaker was tripped by a sibling thread while we slept; reschedule
                    continue

        return total_waited


def reset_rate_limiter(store_name: Optional[str] = None) -> None:
    """
    Reset rate limiting and circuit breaker state.
    If store_name is None, resets all stores globally.
    """
    with _GLOBAL_LOCK:
        if store_name:
            store = store_name.strip()
            _STORE_COOLDOWNS.pop(store, None)
            _NEXT_AVAILABLE_TS.pop(store, None)
            _STORE_CONFIGS.pop(store, None)
            _STORE_LOCKS.pop(store, None)
        else:
            _STORE_COOLDOWNS.clear()
            _NEXT_AVAILABLE_TS.clear()
            _STORE_CONFIGS.clear()
            _STORE_LOCKS.clear()
