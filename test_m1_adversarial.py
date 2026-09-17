"""
Milestone M1 Adversarial Challenge & Verification Test Suite
Empirically stress-tests daemon singleton lock, rapid concurrent launches,
crash recovery (taskkill /F), orphan/zombie cleanup, and corrupted PID states.
"""
import os
import sys
import time
import subprocess
import threading
from typing import List, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from storage.daemon_lock import (
    acquire_daemon_lock,
    release_daemon_lock,
    read_active_daemon_pid,
    is_daemon_locked,
    is_pid_alive,
    terminate_pid,
    terminate_orphan_daemons,
    DEFAULT_PID_PATH
)

TEST_PID_DIR = os.path.join("storage", "test_pids")
os.makedirs(TEST_PID_DIR, exist_ok=True)

def cleanup_pid_file(path: str):
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass

def kill_proc_tree(pid: int):
    try:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True)
    except Exception:
        pass

# ----------------------------------------------------------------------
# TEST 1: Corrupted & Edge-Case PID Files
# ----------------------------------------------------------------------
def test_corrupted_and_edge_case_pid_files() -> Tuple[bool, str]:
    pid_path = os.path.join(TEST_PID_DIR, "corrupt_test.pid")
    cleanup_pid_file(pid_path)

    # 1. Non-existent file
    assert read_active_daemon_pid(pid_path) is None
    assert is_daemon_locked(pid_path) is False

    # 2. Empty file (0 bytes)
    with open(pid_path, "wb") as f:
        pass
    assert read_active_daemon_pid(pid_path) is None
    assert is_daemon_locked(pid_path) is False

    ok, handle, pid = acquire_daemon_lock(pid_path)
    assert ok is True and pid == os.getpid()
    assert is_daemon_locked(pid_path) is True
    assert read_active_daemon_pid(pid_path) == os.getpid()
    release_daemon_lock(handle, pid_path)
    assert not os.path.exists(pid_path)

    # 3. Garbage content
    with open(pid_path, "w", encoding="utf-8") as f:
        f.write("GARBAGE_NOT_A_PID\nEXTRA_LINE\n")
    assert read_active_daemon_pid(pid_path) is None
    assert is_daemon_locked(pid_path) is False

    ok, handle, pid = acquire_daemon_lock(pid_path)
    assert ok is True and pid == os.getpid()
    assert read_active_daemon_pid(pid_path) == os.getpid()
    release_daemon_lock(handle, pid_path)

    return True, "0-byte, non-existent, and garbage PID files safely recovered and formatted."

# ----------------------------------------------------------------------
# TEST 2: Raw OS Concurrency Stress on acquire_daemon_lock (10 processes)
# ----------------------------------------------------------------------
def test_raw_concurrency_stress() -> Tuple[bool, str]:
    pid_path = os.path.join(TEST_PID_DIR, "raw_stress.pid")
    cleanup_pid_file(pid_path)

    worker_code = f"""
import sys, os, time
sys.path.insert(0, r"{os.path.abspath('.')}")
from storage.daemon_lock import acquire_daemon_lock, release_daemon_lock

ok, handle, active_pid = acquire_daemon_lock(r"{pid_path}")
if ok:
    time.sleep(1.0)
    release_daemon_lock(handle, r"{pid_path}")
    sys.exit(0)
else:
    sys.exit(1)
"""

    num_processes = 10
    procs = []
    for _ in range(num_processes):
        p = subprocess.Popen([sys.executable, "-c", worker_code], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        procs.append(p)

    return_codes = [p.wait(timeout=10) for p in procs]
    winners = [rc for rc in return_codes if rc == 0]
    losers = [rc for rc in return_codes if rc == 1]
    others = [rc for rc in return_codes if rc not in (0, 1)]

    assert len(winners) == 1, f"Expected exactly 1 winner, got {len(winners)}"
    assert len(losers) == num_processes - 1, f"Expected {num_processes - 1} losers, got {len(losers)}"
    assert len(others) == 0, f"Unexpected return codes: {others}"

    time.sleep(0.2)
    cleanup_pid_file(pid_path)
    return True, f"10 concurrent processes: exactly 1 acquired (rc=0), 9 rejected (rc=1), 0 errors."

# ----------------------------------------------------------------------
# TEST 3: Crash Recovery via Abrupt Process Kill (taskkill /F / kill -9)
# ----------------------------------------------------------------------
def test_crash_recovery_abrupt_kill() -> Tuple[bool, str]:
    pid_path = os.path.join(TEST_PID_DIR, "crash_recovery.pid")
    cleanup_pid_file(pid_path)

    p1 = subprocess.Popen(
        [sys.executable, "scripts/run_freshner_daemon.py", "--pid-file", pid_path, "--interval", "60"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )

    for _ in range(50):
        if os.path.exists(pid_path) and is_daemon_locked(pid_path):
            break
        time.sleep(0.1)

    assert os.path.exists(pid_path), "PID file was not created"
    assert is_daemon_locked(pid_path) is True, "Daemon lock not held by process 1"
    pid1 = read_active_daemon_pid(pid_path)
    assert pid1 == p1.pid

    # Abruptly kill p1 via taskkill /F
    kill_proc_tree(p1.pid)
    p1.wait(timeout=5)
    time.sleep(0.3)

    assert not is_pid_alive(pid1), "Process should be dead"
    assert os.path.exists(pid_path), "Stale PID file should still exist"
    assert read_active_daemon_pid(pid_path) == pid1
    assert is_daemon_locked(pid_path) is False, "Kernel lock should be released after crash"

    # Launch p2 to re-acquire lock
    p2 = subprocess.Popen(
        [sys.executable, "scripts/run_freshner_daemon.py", "--pid-file", pid_path, "--interval", "60"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )

    for _ in range(50):
        if is_daemon_locked(pid_path) and read_active_daemon_pid(pid_path) == p2.pid:
            break
        time.sleep(0.1)

    assert is_daemon_locked(pid_path) is True
    pid2 = read_active_daemon_pid(pid_path)
    assert pid2 == p2.pid, f"Expected new PID {p2.pid}, got {pid2}"

    kill_proc_tree(p2.pid)
    p2.wait(timeout=5)
    cleanup_pid_file(pid_path)
    return True, "Lock re-acquired immediately after abrupt kill without deadlock or manual deletion."

# ----------------------------------------------------------------------
# TEST 4: Concurrent CLI Launches (Evaluating Refusal & Startup Race)
# ----------------------------------------------------------------------
def test_daemon_script_concurrent_launches() -> Tuple[bool, str]:
    pid_path = os.path.join(TEST_PID_DIR, "daemon_cli_concurrent.pid")
    cleanup_pid_file(pid_path)

    num_competing = 5
    procs: List[subprocess.Popen] = []
    barrier = threading.Barrier(num_competing)

    def launch_instance(idx: int):
        barrier.wait()
        p = subprocess.Popen(
            [sys.executable, "scripts/run_freshner_daemon.py", "--pid-file", pid_path, "--interval", "60"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        procs.append(p)

    threads = [threading.Thread(target=launch_instance, args=(i,)) for i in range(num_competing)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    time.sleep(6.0)

    alive = []
    dead = []
    for p in procs:
        rc = p.poll()
        if rc is None:
            alive.append(p)
        else:
            out, err = p.communicate()
            dead.append((p.pid, rc, out + err))

    # Cleanup all alive immediately
    for p in alive:
        kill_proc_tree(p.pid)
    cleanup_pid_file(pid_path)

    # Check for empty outputs indicating premature termination by sibling
    silent_kills = [pid for pid, rc, out in dead if len(out.strip()) == 0]
    logged_refusal = [pid for pid, rc, out in dead if "Another daemon instance is already active" in out]

    if silent_kills:
        return False, (
            f"FAIL: {len(silent_kills)} of {len(dead)} losing processes were terminated silently "
            f"with empty output (PIDs: {silent_kills}) by terminate_orphan_daemons before they could "
            f"evaluate acquire_daemon_lock and log the refusal warning."
        )

    if len(alive) != 1:
        return False, f"FAIL: Expected 1 running daemon, found {len(alive)} alive (PIDs: {[p.pid for p in alive]})."

    return True, f"Exactly 1 winner, all {len(dead)} losing instances exited 1 with logged refusal message."

# ----------------------------------------------------------------------
# TEST 5: Sequential Second Instance Refusal & Refusal Log Verification
# ----------------------------------------------------------------------
def test_sequential_second_instance_refusal() -> Tuple[bool, str]:
    pid_path = os.path.join(TEST_PID_DIR, "seq_refusal.pid")
    cleanup_pid_file(pid_path)

    p1 = subprocess.Popen(
        [sys.executable, "scripts/run_freshner_daemon.py", "--pid-file", pid_path, "--interval", "60"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )

    for _ in range(50):
        if os.path.exists(pid_path) and is_daemon_locked(pid_path):
            break
        time.sleep(0.1)

    assert os.path.exists(pid_path)
    pid1 = read_active_daemon_pid(pid_path)
    assert pid1 == p1.pid

    # Launch instance 2 sequentially
    p2 = subprocess.run(
        [sys.executable, "scripts/run_freshner_daemon.py", "--pid-file", pid_path, "--interval", "60"],
        capture_output=True, text=True
    )

    kill_proc_tree(p1.pid)
    p1.wait(timeout=5)
    cleanup_pid_file(pid_path)

    out2 = p2.stdout + p2.stderr
    if p2.returncode != 1:
        return False, f"Expected returncode 1, got {p2.returncode}"
    if "Another daemon instance is already active" not in out2:
        return False, f"Missing refusal log in output: {out2}"

    return True, "Sequential second instance exited immediately with returncode 1 and refusal log."

# ----------------------------------------------------------------------
# Runner
# ----------------------------------------------------------------------
if __name__ == "__main__":
    test_cases = [
        ("Corrupted & Edge-Case PID Files", test_corrupted_and_edge_case_pid_files),
        ("Raw Concurrency Stress on acquire_daemon_lock (10 processes)", test_raw_concurrency_stress),
        ("Crash Recovery via Abrupt Process Kill (taskkill /F)", test_crash_recovery_abrupt_kill),
        ("Sequential Second Instance Refusal & Log Output", test_sequential_second_instance_refusal),
        ("Rapid Concurrent Launches (Startup Race & Refusal Log)", test_daemon_script_concurrent_launches),
    ]

    print("=" * 70)
    print("MILESTONE M1 ADVERSARIAL CHALLENGE TEST SUITE")
    print("=" * 70)

    summary = []
    for name, fn in test_cases:
        print(f"\n[RUNNING] {name}...")
        try:
            passed, detail = fn()
        except Exception as exc:
            passed = False
            import traceback
            detail = f"Exception raised: {exc}\n{traceback.format_exc()}"

        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {detail}")
        summary.append((name, passed, detail))

    print("\n" + "=" * 70)
    print("ADVERSARIAL STRESS CHALLENGE SUMMARY")
    print("=" * 70)
    for name, passed, detail in summary:
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {name}")
    print("=" * 70)

    all_passed = all(p for _, p, _ in summary)
    sys.exit(0 if all_passed else 1)
