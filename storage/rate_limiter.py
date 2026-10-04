"""
Centralized, Store-Agnostic Rate Limiter & Circuit Breaker
Thread-safe pacing, per-store sliding slot scheduling, and 429 circuit breaking.
Pure functions only, zero classes (ADR 0005, ADR 0010).
"""
import time
import threading
import email.utils
from typing import Any, Dict, Optional, Tuple, Union

_STORE_LOCKS: Dict[str, threading.RLock] = {}
_STORE_COOLDOWNS: Dict[str, float] = {}       # store -> epoch timestamp when cooldown ends
_NEXT_AVAILABLE_TS: Dict[str, float] = {}     # store -> epoch timestamp when next request can proceed
_STORE_CONFIGS: Dict[str, Dict[str, float]] = {}  # store -> {"requests_per_second": float, "delay_seconds": float}
_GLOBAL_LOCK = threading.RLock()

DEFAULT_REQUESTS_PER_SECOND = 2.0
DEFAULT_DELAY_SECONDS = 0.5
DEFAULT_COOLDOWN_SECONDS = 60.0
MAX_COOLDOWN_SECONDS = 1800.0  # 30-minute safety cap for retailer WAF cooldowns
_CONSECUTIVE_THROTTLES: Dict[str, int] = {}  # store -> consecutive 429/403/block count


def _get_store_lock(store_name: str) -> threading.RLock:
    """Retrieve or initialize a reentrant thread lock dedicated to a specific store."""
    clean_store = (store_name or "default").strip()
    with _GLOBAL_LOCK:
        if clean_store not in _STORE_LOCKS:
            _STORE_LOCKS[clean_store] = threading.RLock()
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


def record_throttle(
    store_name: str,
    threshold: int = 2,
    cooldown_seconds: float = 1200.0
) -> bool:
    """
    Record a rate-limit/block encounter for a store.
    If consecutive throttles reach threshold, automatically trips circuit breaker.
    Returns True if breaker was tripped.
    """
    store = (store_name or "default").strip()
    store_lock = _get_store_lock(store)
    with store_lock:
        curr = _CONSECUTIVE_THROTTLES.get(store, 0) + 1
        _CONSECUTIVE_THROTTLES[store] = curr
        if curr >= threshold:
            trip_circuit_breaker(store, cooldown_seconds)
            return True
        return False


def record_success(store_name: str) -> None:
    """Reset consecutive throttle counter upon successful response."""
    store = (store_name or "default").strip()
    store_lock = _get_store_lock(store)
    with store_lock:
        _CONSECUTIVE_THROTTLES[store] = 0


def create_store_limiter(store_name: str) -> Dict[str, Any]:
    """
    Pure functional closure-based per-store rate limiter and circuit breaker handle.
    Enables store-scoped permit acquisition and circuit tripping without global leakage.
    Zero classes (ADR 0005, ADR 0010).
    """
    store = (store_name or "default").strip()

    def _safe_acquire(*args, **kwargs):
        rps = kwargs.get("requests_per_second", kwargs.get("rps"))
        delay = kwargs.get("delay_seconds", kwargs.get("delay"))
        for a in args:
            if isinstance(a, (int, float)):
                if rps is None:
                    rps = float(a)
                elif delay is None:
                    delay = float(a)
        return acquire_permit(store, rps, delay)

    def _safe_trip(*args, **kwargs):
        cd = kwargs.get("cooldown_seconds", kwargs.get("cooldown", DEFAULT_COOLDOWN_SECONDS))
        for a in args:
            if isinstance(a, (int, float)):
                cd = float(a)
        return trip_circuit_breaker(store, cd)

    def _safe_throttle(*args, **kwargs):
        th = kwargs.get("threshold", 2)
        cd = kwargs.get("cooldown_seconds", kwargs.get("cooldown", 1200.0))
        for a in args:
            if isinstance(a, int):
                th = a
            elif isinstance(a, float):
                cd = a
        return record_throttle(store, th, cd)

    return {
        "store": store,
        "acquire_permit": _safe_acquire,
        "trip_circuit_breaker": _safe_trip,
        "is_circuit_open": lambda: is_circuit_open(store),
        "get_cooldown_remaining": lambda: get_cooldown_remaining(store),
        "record_throttle": _safe_throttle,
        "record_success": lambda: record_success(store),
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


class CircuitBreakerOpenError(Exception):
    """Raised when request permit is denied due to an active circuit breaker cooldown."""
    pass


def acquire_permit(
    store_name: str,
    requests_per_second: Optional[Any] = None,
    delay_seconds: Optional[Any] = None,
    fail_on_circuit_open: bool = True
) -> float:
    """
    Thread-safe permit acquisition for a store.
    Enforces per-store polite request pacing.
    If circuit breaker is open:
    FAIL-FAST IMMEDIATELY in 0.0ms instead of sleeping for minutes!
    Raises CircuitBreakerOpenError if fail_on_circuit_open is True.
    """
    store = (store_name or "default").strip()
    store_lock = _get_store_lock(store)

    with store_lock:
        now = time.time()
        cooldown_end = _STORE_COOLDOWNS.get(store, 0.0)
        if cooldown_end > now:
            if fail_on_circuit_open:
                rem = cooldown_end - now
                raise CircuitBreakerOpenError(f"Circuit breaker open for '{store}' ({rem:.0f}s cooldown remaining)")
            return 0.0

        rps_cfg, delay_cfg = get_store_rate_limits(store)
        rps_val = float(requests_per_second) if isinstance(requests_per_second, (int, float)) else rps_cfg
        delay_val = float(delay_seconds) if isinstance(delay_seconds, (int, float)) else delay_cfg
        min_interval = max(delay_val, 1.0 / rps_val if rps_val > 0 else 0.0)

        prev_next = _NEXT_AVAILABLE_TS.get(store, 0.0)
        scheduled_slot = max(now, prev_next)
        _NEXT_AVAILABLE_TS[store] = scheduled_slot + min_interval
        sleep_duration = scheduled_slot - now

    # Normal polite pacing between consecutive requests (capped at 2.0s max)
    if 0 < sleep_duration <= 2.0:
        time.sleep(sleep_duration)
        return sleep_duration
    return 0.0


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
            _CONSECUTIVE_THROTTLES.pop(store, None)
        else:
            _STORE_COOLDOWNS.clear()
            _NEXT_AVAILABLE_TS.clear()
            _STORE_CONFIGS.clear()
            _STORE_LOCKS.clear()
            _CONSECUTIVE_THROTTLES.clear()
