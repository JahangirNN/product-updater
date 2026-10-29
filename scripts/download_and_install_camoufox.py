"""
Multi-threaded Resilient Camoufox Downloader and Installer
Downloads Camoufox using parallel Range requests, verifies checksum, extracts, and configures cache.
"""
import os
import sys
import time
import hashlib
import zipfile
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import httpx

DOWNLOAD_URL = "https://github.com/daijro/camoufox/releases/download/v156.0.1-beta.36/camoufox-156.0.1-beta.36-win.x86_64.zip"
TOTAL_SIZE = 1311638126
EXPECTED_SHA256 = "096fd4832a7a32f2aa7f7bdd07fe6253dda296cbe783acd7bc2c86cf5ae62031"
VERSION = "156.0.1"
BUILD = "beta.36"
NUM_PARTS = 8

CACHE_DIR = Path(os.environ.get("LOCALAPPDATA", "C:\\Users\\Jahangir\\AppData\\Local")) / "camoufox" / "camoufox" / "Cache"
PARTS_DIR = Path(os.environ.get("LOCALAPPDATA", "C:\\Users\\Jahangir\\AppData\\Local")) / "camoufox" / "download_parts"
DEST_ZIP = Path("C:/Users/Jahangir/Downloads/camoufox-156.0.1-beta.36-win.x86_64.zip")
LOG_FILE = Path(__file__).resolve().parent.parent / "logs" / "camoufox_install.log"


def log(msg: str):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {msg}"
    print(formatted, flush=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(formatted + "\n")


def get_part_ranges(total_size: int, num_parts: int):
    part_size = total_size // num_parts
    ranges = []
    for i in range(num_parts):
        start = i * part_size
        end = total_size - 1 if i == num_parts - 1 else (i + 1) * part_size - 1
        ranges.append((i, start, end))
    return ranges


def download_part(part_idx: int, start: int, end: int, part_path: Path):
    expected_bytes = end - start + 1
    retries = 0
    max_retries = 100

    while retries < max_retries:
        cur_size = part_path.stat().st_size if part_path.exists() else 0
        if cur_size >= expected_bytes:
            return

        range_start = start + cur_size
        headers = {"Range": f"bytes={range_start}-{end}"}

        try:
            with httpx.Client(follow_redirects=True, timeout=60.0) as client:
                with client.stream("GET", DOWNLOAD_URL, headers=headers) as resp:
                    if resp.status_code not in (200, 206):
                        raise RuntimeError(f"HTTP {resp.status_code}")
                    with open(part_path, "ab") as f:
                        for chunk in resp.iter_bytes(chunk_size=256 * 1024):
                            if chunk:
                                f.write(chunk)
            # Verify size
            final_size = part_path.stat().st_size if part_path.exists() else 0
            if final_size >= expected_bytes:
                return
        except Exception as exc:
            retries += 1
            time.sleep(2)


def monitor_progress(ranges, stop_event):
    t0 = time.time()
    last_bytes = 0
    while not stop_event.is_set():
        time.sleep(5)
        total_dl = 0
        for idx, start, end in ranges:
            part_path = PARTS_DIR / f"part_{idx}.bin"
            if part_path.exists():
                total_dl += part_path.stat().st_size
        
        pct = (total_dl / TOTAL_SIZE) * 100
        now = time.time()
        dt = now - t0
        speed = (total_dl / dt) / (1024 * 1024) if dt > 0 else 0
        remaining = TOTAL_SIZE - total_dl
        eta_sec = (remaining / (speed * 1024 * 1024)) if speed > 0 else 0
        eta_m, eta_s = divmod(int(eta_sec), 60)

        log(f"[Progress] {total_dl / (1024*1024):.1f} MB / {TOTAL_SIZE / (1024*1024):.1f} MB ({pct:.1f}%) | Speed: {speed:.2f} MB/s | ETA: {eta_m}m {eta_s:02d}s")
        if total_dl >= TOTAL_SIZE:
            break


def assemble_zip(ranges, dest_path: Path):
    log(f"Assembling {len(ranges)} parts into {dest_path}...")
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(dest_path, "wb") as outfile:
        for idx, _, _ in ranges:
            part_file = PARTS_DIR / f"part_{idx}.bin"
            with open(part_file, "rb") as infile:
                while True:
                    buf = infile.read(4 * 1024 * 1024)
                    if not buf:
                        break
                    outfile.write(buf)
    log(f"Archive assembled: {dest_path.stat().st_size} bytes")


def verify_sha256(file_path: Path, expected_sha: str) -> bool:
    log("Verifying SHA256 checksum...")
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(4 * 1024 * 1024)
            if not chunk:
                break
            sha.update(chunk)
    digest = sha.hexdigest().lower()
    log(f"Calculated SHA256: {digest}")
    log(f"Expected   SHA256: {expected_sha.lower()}")
    return digest == expected_sha.lower()


def install_to_cache(zip_path: Path):
    sha8 = EXPECTED_SHA256[:8]
    version_folder = f"{VERSION}-{BUILD}-{sha8}"
    target_dir = CACHE_DIR / "browsers" / "official" / version_folder
    
    log(f"Extracting Camoufox to {target_dir}...")
    target_dir.mkdir(parents=True, exist_ok=True)
    
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(target_dir)

    # Write version.json
    version_meta = {
        "version": VERSION,
        "build": BUILD,
        "prerelease": False,
        "asset_id": 614464306,
        "asset_size": TOTAL_SIZE,
        "asset_updated_at": "2026-10-06T04:26:46Z",
        "sha256": EXPECTED_SHA256,
        "created_at": "2026-10-06T04:24:51Z"
    }
    with open(target_dir / "version.json", "w", encoding="utf-8") as f:
        json.dump(version_meta, f, indent=2)

    # Set active in config.json
    config_file = CACHE_DIR / "config.json"
    config_data = {}
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config_data = json.load(f)
        except Exception:
            pass
    config_data["active_version"] = f"browsers/official/{version_folder}"
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2)

    # Touch compat flag
    compat_flag = CACHE_DIR / ".0.5_FLAG"
    compat_flag.touch(exist_ok=True)

    log("Camoufox extracted and config registered successfully.")


def verify_camoufox():
    log("Verifying Camoufox via python package...")
    from camoufox.pkgman import camoufox_path, installed_verstr
    path = camoufox_path(download_if_missing=False)
    ver = installed_verstr()
    log(f"Camoufox verification SUCCESS! Version: {ver}, Path: {path}")


def main():
    log("Starting resilient parallel Camoufox downloader...")
    PARTS_DIR.mkdir(parents=True, exist_ok=True)
    ranges = get_part_ranges(TOTAL_SIZE, NUM_PARTS)

    import threading
    stop_event = threading.Event()
    monitor_thread = threading.Thread(target=monitor_progress, args=(ranges, stop_event), daemon=True)
    monitor_thread.start()

    with ThreadPoolExecutor(max_workers=NUM_PARTS) as executor:
        futures = {
            executor.submit(download_part, idx, start, end, PARTS_DIR / f"part_{idx}.bin"): idx
            for idx, start, end in ranges
        }
        for future in as_completed(futures):
            future.result()

    stop_event.set()
    log("All 8 parts downloaded successfully!")

    assemble_zip(ranges, DEST_ZIP)

    if not verify_sha256(DEST_ZIP, EXPECTED_SHA256):
        log("ERROR: SHA256 checksum mismatch!")
        sys.exit(1)

    log("SHA256 checksum verified perfectly.")
    install_to_cache(DEST_ZIP)
    verify_camoufox()

    # Cleanup parts to save space
    log("Cleaning up temporary parts...")
    for idx, _, _ in ranges:
        part_file = PARTS_DIR / f"part_{idx}.bin"
        if part_file.exists():
            part_file.unlink()
    if PARTS_DIR.exists():
        try:
            PARTS_DIR.rmdir()
        except Exception:
            pass

    log("[COMPLETE] Camoufox stealth browser is fully installed, configured, and ready for Nordstrom sweeps!")


if __name__ == "__main__":
    main()
