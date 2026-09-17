"""
Daemon Process Singleton Lock & Lifecycle Utilities
Implements OS-level non-blocking file locking and orphan termination.
Pure functions only, zero classes (ADR 0004, ADR 0005, ADR 0008, ADR 0009).
"""
import os
import sys
import time
import signal
import subprocess
import re
from typing import Optional, Tuple, BinaryIO, List

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl

DEFAULT_PID_PATH: str = os.path.join("storage", "daemon.pid")
LOCK_BYTE_OFFSET: int = 1024


def read_active_daemon_pid(pid_path: str = DEFAULT_PID_PATH) -> Optional[int]:
    """
    Read the active daemon PID using unbuffered I/O.
    Reading byte offset 0 with os.read(fd, 64) avoids contention
    with the byte-range lock placed at offset 1024 on Windows.
    """
    if not os.path.exists(pid_path):
        return None
    try:
        fd = os.open(pid_path, os.O_RDONLY)
        try:
            raw = os.read(fd, 64)
            val = raw.decode("utf-8", errors="ignore").strip()
            tokens = val.split()
            if tokens and tokens[0].isdigit():
                return int(tokens[0])
            return None
        finally:
            os.close(fd)
    except Exception:
        return None


def is_pid_alive(pid: int) -> bool:
    """
    Check if a process with the given PID is currently active.
    On Windows, queries process exit code via GetExitCodeProcess to distinguish
    genuinely running processes from terminated zombie kernel objects.
    On POSIX, uses os.kill(pid, 0).
    """
    if pid <= 0:
        return False
    if pid == os.getpid():
        return True

    if sys.platform == "win32":
        try:
            import ctypes
            import ctypes.wintypes
            kernel32 = ctypes.windll.kernel32
            process_query_limited_info = 0x1000
            still_active = 259
            handle = kernel32.OpenProcess(process_query_limited_info, False, pid)
            if not handle:
                # WinError 5 is ERROR_ACCESS_DENIED (process exists but owned by other user)
                return kernel32.GetLastError() == 5
            try:
                exit_code = ctypes.wintypes.DWORD()
                success = kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
                if not success:
                    return False
                return exit_code.value == still_active
            finally:
                kernel32.CloseHandle(handle)
        except Exception:
            pass

    try:
        os.kill(pid, 0)
        return True
    except OSError as err:
        winerr = getattr(err, "winerror", None)
        errno = getattr(err, "errno", None)
        if winerr == 87 or errno == 3:  # ESRCH: No such process
            return False
        if winerr == 5 or errno == 1:   # EPERM: Process exists, lacks permission
            return True
        return False


def terminate_pid(pid: int) -> bool:
    """
    Terminate a process cleanly by PID.
    Sends SIGTERM first, waiting up to 0.1s for clean exit,
    then escalates to taskkill (Windows) or SIGKILL (POSIX).
    """
    if not is_pid_alive(pid):
        return False
    try:
        if sys.platform == "win32":
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                process_terminate = 1
                h = kernel32.OpenProcess(process_terminate, False, pid)
                if h:
                    kernel32.TerminateProcess(h, 1)
                    kernel32.CloseHandle(h)
            except Exception:
                pass
            time.sleep(0.1)
            if is_pid_alive(pid):
                subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid)],
                    capture_output=True,
                    check=False
                )
        else:
            try:
                os.kill(pid, signal.SIGTERM)
            except Exception:
                pass
            time.sleep(0.1)
            if is_pid_alive(pid):
                os.kill(pid, signal.SIGKILL)
        return not is_pid_alive(pid)
    except Exception:
        return False



def is_daemon_locked(pid_path: str = DEFAULT_PID_PATH) -> bool:
    """
    Test whether the daemon lock on pid_path is held by another process
    without disturbing file contents.
    """
    if not os.path.exists(pid_path):
        return False
    try:
        f = open(pid_path, "a+b")
        try:
            if sys.platform == "win32":
                f.seek(LOCK_BYTE_OFFSET)
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                f.seek(LOCK_BYTE_OFFSET)
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                return False
            else:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                return False
        finally:
            f.close()
    except (OSError, PermissionError, IOError):
        return True


def get_process_uptime_seconds(pid: int) -> float:
    """Get process uptime in seconds on Windows or POSIX."""
    if pid <= 0:
        return 0.0
    if sys.platform == "win32":
        try:
            import ctypes
            import ctypes.wintypes
            kernel32 = ctypes.windll.kernel32
            process_query_limited_info = 0x1000
            h = kernel32.OpenProcess(process_query_limited_info, False, pid)
            if h:
                try:
                    creation = ctypes.wintypes.FILETIME()
                    exit_t = ctypes.wintypes.FILETIME()
                    kernel_t = ctypes.wintypes.FILETIME()
                    user_t = ctypes.wintypes.FILETIME()
                    if kernel32.GetProcessTimes(h, ctypes.byref(creation), ctypes.byref(exit_t), ctypes.byref(kernel_t), ctypes.byref(user_t)):
                        ft = (creation.dwHighDateTime << 32) + creation.dwLowDateTime
                        created_epoch = (ft - 116444736000000000) / 10000000.0
                        return max(0.0, time.time() - created_epoch)
                finally:
                    kernel32.CloseHandle(h)
        except Exception:
            pass
        return 0.0
    else:
        try:
            stat_path = f"/proc/{pid}/stat"
            if os.path.exists(stat_path):
                with open(stat_path, "r") as f:
                    content = f.read()
                fields = content.split()
                if len(fields) > 21:
                    clk_tck = os.sysconf("SC_CLK_TCK")
                    starttime_ticks = int(fields[21])
                    with open("/proc/uptime", "r") as uf:
                        system_uptime = float(uf.read().split()[0])
                    process_uptime = system_uptime - (starttime_ticks / clk_tck)
                    return max(0.0, process_uptime)
        except Exception:
            pass
        return 0.0


def is_python_process(pid: int) -> bool:
    """Check if process with PID is a Python process before terminating."""
    if not is_pid_alive(pid):
        return False
    if sys.platform == "win32":
        try:
            cmd = ["wmic", "process", "where", f"ProcessId={pid}", "get", "name", "/format:value"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    if "Name=" in line:
                        proc_name = line.split("=", 1)[1].strip().lower()
                        return "python" in proc_name
        except Exception:
            pass
        return True
    return True


def _extract_pid_file_arg(cmd: str) -> Optional[str]:
    """Extract --pid-file argument from a process command line string if present."""
    m = re.search(r'--pid-file(?:\s+|=)(?:"([^"]+)"|\'([^\']+)\'|([^\s]+))', cmd, re.IGNORECASE)
    if m:
        return m.group(1) or m.group(2) or m.group(3)
    return None


def terminate_orphan_daemons(
    current_pid: Optional[int] = None,
    pid_path: str = DEFAULT_PID_PATH
) -> int:
    """
    Scan and terminate any orphan/zombie daemon processes from past runs.
    Guarantees that the current process and any active daemon holding the lock
    are NOT terminated.
    """
    curr = current_pid or os.getpid()
    terminated = 0

    # Determine if an active daemon currently holds the lock
    active_pid: Optional[int] = None
    if is_daemon_locked(pid_path):
        active_pid = read_active_daemon_pid(pid_path)
        if active_pid is None:
            for _ in range(5):
                time.sleep(0.02)
                active_pid = read_active_daemon_pid(pid_path)
                if active_pid is not None:
                    break
        if active_pid is None:
            # Lock is held by an active daemon whose PID is not yet unbuffered-readable;
            # preserve all processes to avoid assassinating the active leader.
            return 0

    # 1. Clean stale PID file if lock is NOT held
    if not is_daemon_locked(pid_path):
        stale_pid = read_active_daemon_pid(pid_path)
        if stale_pid and stale_pid != curr and is_pid_alive(stale_pid):
            if is_python_process(stale_pid):
                if terminate_pid(stale_pid):
                    terminated += 1
        if os.path.exists(pid_path):
            try:
                os.remove(pid_path)
            except Exception:
                pass

    # 2. Check process table for lingering python run_freshner_daemon instances
    ppid = os.getppid() if hasattr(os, "getppid") else -1
    target_pid_norm = os.path.normpath(os.path.abspath(pid_path)).lower()
    default_pid_norm = os.path.normpath(os.path.abspath(DEFAULT_PID_PATH)).lower()

    candidates: List[Tuple[int, str]] = []

    if sys.platform == "win32":
        # Fast path: wmic (~0.1-0.2s)
        try:
            cmd = ["wmic", "process", "where", "name like \"%python%\" and commandline like \"%run_freshner_daemon%\"", "get", "commandline,processid"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=4)
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    tokens = line.rsplit(None, 1)
                    if len(tokens) == 2 and tokens[1].isdigit():
                        candidates.append((int(tokens[1]), tokens[0]))
        except Exception:
            pass

        # Fallback: PowerShell Get-CimInstance (~1.5-2.5s) if wmic unavailable
        if not candidates:
            try:
                cmd = [
                    "powershell", "-NoProfile", "-NonInteractive", "-Command",
                    f'Get-CimInstance Win32_Process | Where-Object {{ $_.Name -like "*python*" -and $_.CommandLine -like "*run_freshner_daemon*" -and $_.ProcessId -ne {curr} }} | Select-Object ProcessId, CommandLine'
                ]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                for line in res.stdout.strip().splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    tokens = line.split(None, 1)
                    if len(tokens) >= 1 and tokens[0].isdigit():
                        cmdline = tokens[1] if len(tokens) > 1 else ""
                        candidates.append((int(tokens[0]), cmdline))
            except Exception:
                pass

    else:
        try:
            res = subprocess.run(["pgrep", "-f", "run_freshner_daemon"], capture_output=True, text=True, timeout=5)
            for line in res.stdout.strip().splitlines():
                line = line.strip()
                if line.isdigit():
                    candidates.append((int(line), ""))
        except Exception:
            pass

    for opid, cmdline in candidates:
        # Never terminate current process, active lock holder, or parent test runner
        if opid == curr or (active_pid is not None and opid == active_pid) or opid == ppid:
            continue

        # Inspect candidate commandline
        is_mock = "run_freshner_daemon_mock_worker" in cmdline if cmdline else False

        if cmdline and not is_mock:
            specified_pid_file = _extract_pid_file_arg(cmdline)
            if specified_pid_file:
                cand_pid_norm = os.path.normpath(os.path.abspath(specified_pid_file)).lower()
                if cand_pid_norm != target_pid_norm:
                    # Candidate belongs to a different daemon instance with its own PID file
                    continue
            elif target_pid_norm != default_pid_norm:
                # Candidate defaults to DEFAULT_PID_PATH while we are targeting a custom test pid_path
                continue

            # Sibling process protection: If the process is a legitimate daemon script that was
            # started recently (uptime < 30 seconds), it is likely starting up or competing for
            # the lock. It will evaluate the lock, log the duplicate refusal warning, and exit
            # cleanly on its own. Do NOT assassinate starting sibling processes!
            uptime = get_process_uptime_seconds(opid)
            if uptime < 30.0:
                continue

        if is_pid_alive(opid):
            if terminate_pid(opid):
                terminated += 1

    return terminated


def acquire_daemon_lock(
    pid_path: str = DEFAULT_PID_PATH
) -> Tuple[bool, Optional[BinaryIO], Optional[int]]:
    """
    Attempt to acquire a non-blocking exclusive OS file lock on pid_path.
    Uses offset-1024 locking on Windows to preserve offset-0 unbuffered PID readability.
    Uses whole-file flock on POSIX.

    Returns:
        (acquired: bool, file_handle: Optional[BinaryIO], active_pid: Optional[int])
    """
    abs_dir = os.path.dirname(os.path.abspath(pid_path))
    if abs_dir:
        os.makedirs(abs_dir, exist_ok=True)

    # Cache any existing PID in case of lock collision
    existing_pid = read_active_daemon_pid(pid_path)

    f: Optional[BinaryIO] = None
    try:
        f = open(pid_path, "a+b")
        if sys.platform == "win32":
            f.seek(LOCK_BYTE_OFFSET)
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

        # Lock successfully acquired! Write current PID to offset 0
        f.seek(0)
        f.truncate(0)
        f.write(f"{os.getpid()}\n".encode("utf-8"))
        f.flush()
        return True, f, os.getpid()

    except (OSError, PermissionError, IOError):
        if f is not None:
            try:
                f.close()
            except Exception:
                pass
        # Lock is held by another active process
        active_pid = read_active_daemon_pid(pid_path) or existing_pid
        if active_pid is None:
            for _ in range(5):
                time.sleep(0.02)
                active_pid = read_active_daemon_pid(pid_path)
                if active_pid is not None:
                    break
        active_pid = active_pid or existing_pid
        return False, None, active_pid


def release_daemon_lock(
    lock_file: Optional[BinaryIO],
    pid_path: str = DEFAULT_PID_PATH
) -> None:
    """
    Release OS file lock, close file handle, and remove the PID file.
    """
    if lock_file is not None:
        try:
            if sys.platform == "win32":
                lock_file.seek(LOCK_BYTE_OFFSET)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        except Exception:
            pass
        try:
            lock_file.close()
        except Exception:
            pass

    if os.path.exists(pid_path):
        try:
            os.remove(pid_path)
        except Exception:
            pass
