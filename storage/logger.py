"""
Centralized Logging Module for Product Updater
Provides pure functional structured logging powered by Loguru with dual-sink file routing:
1. logs/freshner.log: General operational and sync metrics (INFO+)
2. logs/errors.log: Dedicated error isolation with rich diagnostics and stack traces (ERROR+)
Pure functions only, zero classes (ADR 0005, ADR 0009).
"""
import os
import sys
from typing import Any, Optional

_INITIALIZED = False

try:
    from loguru import logger as _loguru_logger
    _HAS_LOGURU = True
except ImportError:
    _loguru_logger = None
    _HAS_LOGURU = False
    import logging as _std_logging


_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def init_logger(
    log_dir: str = "logs",
    general_log_name: str = "freshner.log",
    error_log_name: str = "errors.log",
    shopify_error_log_name: str = "shopify_errors.log",
    rotation_general: str = "50 MB",
    rotation_error: str = "50 MB",
    rotation_shopify: str = "20 MB",
    retention_general: str = "14 days",
    retention_error: str = "30 days",
    retention_shopify: str = "30 days",
    console_level: str = "INFO"
) -> None:
    """
    Initialize centralized logging with dual file sinks, dedicated Shopify error sink,
    and colorized console output.
    Pure functional setup. Safe to call multiple times (idempotent).
    """
    global _INITIALIZED
    if _INITIALIZED:
        return

    full_log_dir = os.path.join(_PROJECT_ROOT, log_dir) if not os.path.isabs(log_dir) else log_dir
    os.makedirs(full_log_dir, exist_ok=True)
    general_log_path = os.path.join(full_log_dir, general_log_name)
    error_log_path = os.path.join(full_log_dir, error_log_name)
    shopify_log_path = os.path.join(full_log_dir, shopify_error_log_name)

    if _HAS_LOGURU and _loguru_logger is not None:
        # Remove default handler
        _loguru_logger.remove()

        # 1. Console Sink with colorized levels and error highlighting
        console_fmt = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        )
        _loguru_logger.add(
            sys.stdout,
            format=console_fmt,
            level=console_level,
            colorize=True,
            enqueue=True
        )

        # 2. General Operational Log Sink (INFO+)
        file_fmt = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{line} - {message}"
        _loguru_logger.add(
            general_log_path,
            format=file_fmt,
            level="INFO",
            rotation=rotation_general,
            retention=retention_general,
            encoding="utf-8",
            enqueue=True
        )

        # 3. Highlighted General Error Isolation Sink (ERROR+ with backtrace & diagnosis)
        error_fmt = (
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{line} - {message}\n"
            "{exception}"
        )
        _loguru_logger.add(
            error_log_path,
            format=error_fmt,
            level="ERROR",
            rotation=rotation_error,
            retention=retention_error,
            encoding="utf-8",
            backtrace=True,
            diagnose=True,
            enqueue=True
        )

        # 4. Dedicated Shopify Error & Warning Isolation Sink (WARNING+)
        shopify_fmt = (
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{line} - {message}\n"
            "{exception}"
        )
        _loguru_logger.add(
            shopify_log_path,
            format=shopify_fmt,
            level="WARNING",
            filter=lambda record: bool(record["extra"].get("shopify")) or "shopify" in record["message"].lower(),
            rotation=rotation_shopify,
            retention=retention_shopify,
            encoding="utf-8",
            backtrace=True,
            diagnose=True,
            enqueue=True
        )
    else:
        # Graceful fallback to standard logging
        root = _std_logging.getLogger()
        root.setLevel(_std_logging.INFO)
        formatter = _std_logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d - %(message)s")

        sh = _std_logging.StreamHandler(sys.stdout)
        sh.setFormatter(formatter)
        root.addHandler(sh)

        fh_general = _std_logging.FileHandler(general_log_path, encoding="utf-8")
        fh_general.setLevel(_std_logging.INFO)
        fh_general.setFormatter(formatter)
        root.addHandler(fh_general)

        fh_error = _std_logging.FileHandler(error_log_path, encoding="utf-8")
        fh_error.setLevel(_std_logging.ERROR)
        fh_error.setFormatter(formatter)
        root.addHandler(fh_error)

        fh_shopify = _std_logging.FileHandler(shopify_log_path, encoding="utf-8")
        fh_shopify.setLevel(_std_logging.WARNING)
        fh_shopify.setFormatter(formatter)
        root.addHandler(fh_shopify)

    _INITIALIZED = True


def log_info(message: str, **kwargs: Any) -> None:
    """Log informational message to console and freshner.log."""
    if not _INITIALIZED:
        init_logger()
    if _HAS_LOGURU and _loguru_logger is not None:
        _loguru_logger.opt(depth=1).info(message, **kwargs)
    else:
        _std_logging.info(message)


def log_success(message: str, **kwargs: Any) -> None:
    """Log success message (highlighted green in Loguru)."""
    if not _INITIALIZED:
        init_logger()
    if _HAS_LOGURU and _loguru_logger is not None:
        _loguru_logger.opt(depth=1).success(message, **kwargs)
    else:
        _std_logging.info(f"[SUCCESS] {message}")


def log_warning(message: str, **kwargs: Any) -> None:
    """Log warning message (yellow highlight)."""
    if not _INITIALIZED:
        init_logger()
    if _HAS_LOGURU and _loguru_logger is not None:
        _loguru_logger.opt(depth=1).warning(message, **kwargs)
    else:
        _std_logging.warning(message)


def log_error(message: str, exc: Optional[BaseException] = None, **kwargs: Any) -> None:
    """
    Log error message with optional exception diagnostics to console, freshner.log,
    and isolated highlighted errors.log.
    """
    if not _INITIALIZED:
        init_logger()
    if _HAS_LOGURU and _loguru_logger is not None:
        if exc:
            _loguru_logger.opt(depth=1, exception=exc).error(message, **kwargs)
        else:
            _loguru_logger.opt(depth=1).error(message, **kwargs)
    else:
        _std_logging.error(message, exc_info=exc)


def log_critical(message: str, exc: Optional[BaseException] = None, **kwargs: Any) -> None:
    """Log critical failure message to all sinks and errors.log."""
    if not _INITIALIZED:
        init_logger()
    if _HAS_LOGURU and _loguru_logger is not None:
        if exc:
            _loguru_logger.opt(depth=1, exception=exc).critical(message, **kwargs)
        else:
            _loguru_logger.opt(depth=1).critical(message, **kwargs)
    else:
        _std_logging.critical(message, exc_info=exc)


def log_delta(action: str, handle: str, details: str) -> None:
    """
    Log catalog delta shift event (price change or stock update) with high visibility.
    """
    if not _INITIALIZED:
        init_logger()
    msg = f"[DELTA:{action.upper()}] {handle} -> {details}"
    if _HAS_LOGURU and _loguru_logger is not None:
        _loguru_logger.opt(depth=1).info(msg)
    else:
        _std_logging.info(msg)


def log_shopify_error(message: str, exc: Optional[BaseException] = None, **kwargs: Any) -> None:
    """
    Log Shopify-specific errors directly to logs/shopify_errors.log, errors.log, and console.
    """
    if not _INITIALIZED:
        init_logger()
    prefix = "" if message.startswith("[SHOPIFY") else "[SHOPIFY ERROR] "
    full_msg = f"{prefix}{message}"
    if _HAS_LOGURU and _loguru_logger is not None:
        bound = _loguru_logger.bind(shopify=True)
        if exc:
            bound.opt(depth=1, exception=exc).error(full_msg, **kwargs)
        else:
            bound.opt(depth=1).error(full_msg, **kwargs)
    else:
        _std_logging.error(full_msg, exc_info=exc)


def log_shopify_warning(message: str, **kwargs: Any) -> None:
    """
    Log Shopify-specific warnings directly to logs/shopify_errors.log and console.
    """
    if not _INITIALIZED:
        init_logger()
    prefix = "" if message.startswith("[SHOPIFY") else "[SHOPIFY WARN] "
    full_msg = f"{prefix}{message}"
    if _HAS_LOGURU and _loguru_logger is not None:
        _loguru_logger.bind(shopify=True).opt(depth=1).warning(full_msg, **kwargs)
    else:
        _std_logging.warning(full_msg)


def log_shopify_success(message: str, **kwargs: Any) -> None:
    """
    Log Shopify successful sync operations to freshner.log and console.
    """
    if not _INITIALIZED:
        init_logger()
    prefix = "" if message.startswith("[SHOPIFY") else "[SHOPIFY SYNC] "
    full_msg = f"{prefix}{message}"
    if _HAS_LOGURU and _loguru_logger is not None:
        _loguru_logger.bind(shopify=True).opt(depth=1).success(full_msg, **kwargs)
    else:
        _std_logging.info(full_msg)

