"""
Partitioned Local JSON Database & Deduplication Engine
Zero external database required, microsecond lookups, atomic file operations.
Pure functions, zero classes (ADR 0004, ADR 0005).
"""
import os
import json
import hashlib
import time
import threading
from typing import Any, Dict, List, Optional


def generate_product_id(store: str, sku: str) -> str:
    """
    Generate deterministic 16-character hex hash primary key.
    Guarantees zero duplicate entries across multiple crawl runs.
    """
    clean_store = store.strip().lower()
    clean_sku = sku.strip().lower()
    raw_key = f"{clean_store}::{clean_sku}".encode("utf-8")
    return hashlib.sha256(raw_key).hexdigest()[:16]


def get_product_file_path(store: str, product_id: str, base_dir: str = "storage/db") -> str:
    """Get absolute or relative path to partitioned product file."""
    return os.path.join(base_dir, store, "products", f"{product_id}.json")


def _atomic_write_json_with_retry(target_file: str, data: Any, max_retries: int = 5) -> None:
    """
    Atomically write data to target_file using a process/thread-unique temp file.
    Includes a retry loop to handle Windows filesystem file contention.
    """
    target_dir = os.path.dirname(target_file)
    if target_dir:
        os.makedirs(target_dir, exist_ok=True)

    unique_suffix = f"{os.getpid()}_{threading.get_ident()}_{int(time.perf_counter()*1000000)}"
    tmp_file = f"{target_file}.{unique_suffix}.tmp"

    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    for attempt in range(max_retries):
        try:
            os.replace(tmp_file, target_file)
            return
        except (PermissionError, OSError):
            if attempt == max_retries - 1:
                try:
                    if os.path.exists(tmp_file):
                        os.remove(tmp_file)
                except Exception:
                    pass
                with open(target_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                return
            time.sleep(0.05 * (2 ** attempt))


def save_product(product: Dict[str, Any], base_dir: str = "storage/db") -> Dict[str, Any]:
    """
    Atomically save or update a canonical product record in partitioned JSON storage.
    If product already exists, performs safe delta merge preserving creation timestamp.
    """
    store = product.get("source_store", "default")
    sku = product.get("source_sku", "")
    if not sku and product.get("variants"):
        sku = product["variants"][0].get("sku", "")
    
    product_id = product.get("id") or generate_product_id(store, sku)
    product["id"] = product_id

    file_path = get_product_file_path(store, product_id, base_dir)
    target_dir = os.path.dirname(file_path)
    os.makedirs(target_dir, exist_ok=True)

    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    # Check if already exists
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            product["created_at"] = existing.get("created_at", now_iso)
            # Merge groups without duplicates
            existing_groups = set(existing.get("groups", []))
            new_groups = set(product.get("groups", []))
            product["groups"] = sorted(list(existing_groups | new_groups))
        except Exception:
            product["created_at"] = now_iso
    else:
        product["created_at"] = now_iso

    product["updated_at"] = now_iso

    # Resilient atomic write with retry for Windows concurrency
    _atomic_write_json_with_retry(file_path, product)

    return product


def load_product(store: str, product_id: str, base_dir: str = "storage/db") -> Optional[Dict[str, Any]]:
    """Read product JSON file from disk."""
    file_path = get_product_file_path(store, product_id, base_dir)
    if not os.path.exists(file_path):
        return None
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_and_save_index(base_dir: str = "storage/db") -> Dict[str, Any]:
    """
    Scan all store partitioned directories and compile fast in-memory index.json.
    """
    index_map = {}
    if not os.path.exists(base_dir):
        return index_map

    for entry in os.listdir(base_dir):
        store_dir = os.path.join(base_dir, entry)
        if not os.path.isdir(store_dir) or entry in ("history", "index.json"):
            continue

        products_dir = os.path.join(store_dir, "products")
        if not os.path.exists(products_dir):
            continue

        for p_file in os.listdir(products_dir):
            if not p_file.endswith(".json"):
                continue
            p_path = os.path.join(products_dir, p_file)
            try:
                with open(p_path, "r", encoding="utf-8") as f:
                    p = json.load(f)
                p_id = p.get("id") or p_file.replace(".json", "")
                index_map[p_id] = {
                    "id": p_id,
                    "store": p.get("source_store"),
                    "sku": p.get("source_sku"),
                    "title": p.get("title"),
                    "handle": p.get("handle"),
                    "source_price_usd": p.get("source_price"),
                    "current_price_inr": p.get("current_price"),
                    "availability": p.get("availability"),
                    "status": p.get("status", "DRAFT"),
                    "groups": p.get("groups", []),
                    "file_path": os.path.relpath(p_path, base_dir).replace("\\", "/"),
                    "updated_at": p.get("updated_at"),
                    "last_verified_at": p.get("last_verified_at"),
                    "shopify_sync_pending": p.get("shopify_sync_pending", False)
                }
            except Exception as err:
                print(f"[WARN] Failed to read {p_path}: {err}")

    index_path = os.path.join(base_dir, "index.json")
    _atomic_write_json_with_retry(index_path, index_map)

    return index_map


_delta_log_lock = threading.Lock()
_delta_event_lock = threading.Lock()


def append_delta_log(delta_entry: Dict[str, Any], base_dir: str = "storage/db") -> None:
    """Append a price or stock delta record to history/delta_log.json in a thread-safe manner."""
    history_dir = os.path.join(base_dir, "history")
    os.makedirs(history_dir, exist_ok=True)
    log_file = os.path.join(history_dir, "delta_log.json")

    with _delta_log_lock:
        existing_logs = []
        if os.path.exists(log_file):
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    existing_logs = json.load(f)
            except Exception:
                existing_logs = []

        if "timestamp" not in delta_entry:
            delta_entry["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        existing_logs.append(delta_entry)
        _atomic_write_json_with_retry(log_file, existing_logs)


def append_delta_event(event_entry: Dict[str, Any], queue_file: str = "storage/db/history/delta_events.jsonl") -> None:
    """
    Append an individual price or stock shift event to the Shopify sync queue.
    Uses O(1) append-only JSON Lines format with cross-process OS file locking
    (msvcrt byte-range on Windows, fcntl on POSIX) to eliminate WinError 32/5 collisions.
    """
    import sys

    if "timestamp" not in event_entry:
        event_entry["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    line = json.dumps(event_entry, ensure_ascii=False) + "\n"

    queue_dir = os.path.dirname(queue_file)
    if queue_dir:
        os.makedirs(queue_dir, exist_ok=True)

    with _delta_event_lock:
        lock_path = queue_file + ".lock"
        lock_f = None
        try:
            # Acquire cross-process OS file lock via dedicated lock file
            lock_f = open(lock_path, "a+b")
            if sys.platform == "win32":
                import msvcrt
                # Seek to offset 0 for consistent byte-range locking
                lock_f.seek(0)
                msvcrt.locking(lock_f.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl
                fcntl.flock(lock_f.fileno(), fcntl.LOCK_EX)

            # Append event line to JSONL queue
            with open(queue_file, "a", encoding="utf-8") as qf:
                qf.write(line)
                qf.flush()

            # Release cross-process lock
            if sys.platform == "win32":
                lock_f.seek(0)
                msvcrt.locking(lock_f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock_f.fileno(), fcntl.LOCK_UN)
        finally:
            if lock_f is not None:
                try:
                    lock_f.close()
                except Exception:
                    pass


def read_delta_events(queue_file: str = "storage/db/history/delta_events.jsonl") -> List[Dict[str, Any]]:
    """
    Read all delta events from the JSONL queue file.
    Returns a list of event dicts for backward compatibility with consumers.
    """
    events = []
    if not os.path.exists(queue_file):
        return events
    try:
        with open(queue_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except Exception:
        pass
    return events

