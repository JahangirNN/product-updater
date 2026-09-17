"""
Adversarial Empirical Stress Test Suite for Milestone M1
Tests:
1. Orphan Process Detection & Termination (detached mock processes)
2. Active Daemon Strict Preservation (active daemon holding lock vs orphan processes)
3. Stale PID File Cleanup (dead PID)
4. Stale PID File with Live Unlocked Process
5. Concurrency Race & Singleton Lock Mutex (Exit Code 1)
6. High Concurrency Lock Race (10 Concurrent Callers)
7. Rapid Acquire/Release Cycles (50 iterations)
8. Simulated Abrupt Crash (SIGKILL / taskkill /F recovery)
9. Corrupted/Malformed PID Files
10. Active Lock with Empty/Unreadable PID (Edge case verification)
"""
import os
import sys
import time
import subprocess
import threading
from typing import List

# Ensure project root is on sys.path
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from storage.daemon_lock import (
    acquire_daemon_lock,
    release_daemon_lock,
    read_active_daemon_pid,
    is_pid_alive,
    terminate_pid,
    terminate_orphan_daemons,
    is_daemon_locked,
    DEFAULT_PID_PATH
)

TEST_PID_PATH = os.path.join("storage", "test_daemon_stress.pid")


def cleanup_test_file(path=TEST_PID_PATH):
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass


def spawn_mock_orphan(duration: int = 60) -> subprocess.Popen:
    """
    Spawns a detached python process whose command line contains 'run_freshner_daemon'.
    """
    code = f"import time\n# run_freshner_daemon mock\ntime.sleep({duration})\n"
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP

    proc = subprocess.Popen(
        [sys.executable, "-c", code, "--name=run_freshner_daemon_mock_worker"],
        creationflags=creationflags
    )
    return proc


def test_orphan_termination_basic():
    print("\n--- [CHALLENGE 1] Orphan Process Detection and Termination ---")
    cleanup_test_file()
    
    # Spawn 3 mock orphan processes
    orphans = [spawn_mock_orphan(duration=60) for _ in range(3)]
    pids = [p.pid for p in orphans]
    print(f"Spawned 3 mock orphans with PIDs: {pids}")
    time.sleep(0.5)

    for pid in pids:
        assert is_pid_alive(pid), f"Mock orphan PID {pid} should be alive initially"

    # Call terminate_orphan_daemons
    terminated = terminate_orphan_daemons(pid_path=TEST_PID_PATH)
    print(f"terminate_orphan_daemons returned: {terminated}")
    time.sleep(0.5)

    dead_count = 0
    for pid in pids:
        alive = is_pid_alive(pid)
        print(f"Orphan PID {pid} alive status: {alive}")
        if not alive:
            dead_count += 1

    assert dead_count == 3, f"Expected all 3 orphans to be terminated, but {3 - dead_count} still alive!"
    print("PASS: All detached mock orphans were detected and terminated.")


def test_active_daemon_preservation():
    print("\n--- [CHALLENGE 2] Active Daemon Strict Preservation ---")
    cleanup_test_file()

    # Launch legitimate daemon instance with noop store filter to prevent network/browser scraping
    daemon_proc = subprocess.Popen(
        [sys.executable, "scripts/run_freshner_daemon.py", "--pid-file", TEST_PID_PATH, "--interval", "60", "--store", "noop_store"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    print(f"Spawned legitimate daemon PID: {daemon_proc.pid}")

    # Wait for daemon to acquire lock and write PID (up to 10s)
    for _ in range(100):
        if is_daemon_locked(TEST_PID_PATH):
            break
        if daemon_proc.poll() is not None:
            out, err = daemon_proc.communicate()
            print(f"Daemon died prematurely with code {daemon_proc.poll()}:\nSTDOUT: {out}\nSTDERR: {err}")
            break
        time.sleep(0.1)

    assert is_daemon_locked(TEST_PID_PATH), "Active daemon failed to acquire lock in time!"
    active_pid = read_active_daemon_pid(TEST_PID_PATH)
    print(f"Active daemon lock confirmed. PID in file: {active_pid} (proc.pid: {daemon_proc.pid})")
    assert active_pid == daemon_proc.pid, f"PID mismatch: {active_pid} vs {daemon_proc.pid}"

    # Now spawn 2 mock detached orphan processes
    orphan1 = spawn_mock_orphan(duration=60)
    orphan2 = spawn_mock_orphan(duration=60)
    orphan_pids = [orphan1.pid, orphan2.pid]
    print(f"Spawned 2 mock orphans alongside active daemon: {orphan_pids}")
    time.sleep(0.5)

    assert is_pid_alive(orphan1.pid), "Orphan 1 should be alive"
    assert is_pid_alive(orphan2.pid), "Orphan 2 should be alive"
    assert is_pid_alive(daemon_proc.pid), "Active daemon should be alive"

    # Run terminate_orphan_daemons
    terminated = terminate_orphan_daemons(pid_path=TEST_PID_PATH)
    print(f"terminate_orphan_daemons returned: {terminated}")
    time.sleep(0.5)

    # CRUCIAL ASSERTION: Active daemon MUST NOT be terminated!
    assert is_pid_alive(daemon_proc.pid), "FATAL BUG: Active daemon was terminated by terminate_orphan_daemons!"
    assert is_daemon_locked(TEST_PID_PATH), "FATAL BUG: Lock was lost on active daemon!"
    assert read_active_daemon_pid(TEST_PID_PATH) == daemon_proc.pid, "PID file was modified or corrupted!"

    # Orphans MUST be terminated!
    assert not is_pid_alive(orphan1.pid), f"Orphan 1 ({orphan1.pid}) was not terminated!"
    assert not is_pid_alive(orphan2.pid), f"Orphan 2 ({orphan2.pid}) was not terminated!"

    print("PASS: Active daemon strictly preserved while both orphans were terminated.")

    # Clean up active daemon
    terminate_pid(daemon_proc.pid)
    daemon_proc.wait(timeout=5)
    time.sleep(0.3)
    cleanup_test_file()


def test_stale_pid_dead_process():
    print("\n--- [CHALLENGE 3] Stale PID File with Dead Process Cleanup ---")
    cleanup_test_file()

    # Write non-existent PID
    fake_pid = 999988
    os.makedirs(os.path.dirname(TEST_PID_PATH), exist_ok=True)
    with open(TEST_PID_PATH, "w") as f:
        f.write(f"{fake_pid}\n")

    assert os.path.exists(TEST_PID_PATH)
    assert not is_daemon_locked(TEST_PID_PATH)

    terminated = terminate_orphan_daemons(pid_path=TEST_PID_PATH)
    print(f"terminate_orphan_daemons returned: {terminated}")

    assert not os.path.exists(TEST_PID_PATH), "Stale PID file was not removed!"
    print("PASS: Stale PID file for non-existent process removed cleanly.")


def test_stale_pid_live_process():
    print("\n--- [CHALLENGE 4] Stale PID File Pointing to Live Unlocked Process ---")
    cleanup_test_file()

    # Spawn a detached worker process that does NOT hold the lock
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time\ntime.sleep(60)\n"],
        creationflags=subprocess.DETACHED_PROCESS if sys.platform == "win32" else 0
    )
    print(f"Spawned unlocked process PID: {proc.pid}")
    time.sleep(0.3)
    assert is_pid_alive(proc.pid)

    # Write its PID to TEST_PID_PATH without acquiring lock
    with open(TEST_PID_PATH, "w") as f:
        f.write(f"{proc.pid}\n")

    assert os.path.exists(TEST_PID_PATH)
    assert not is_daemon_locked(TEST_PID_PATH)

    # Terminate orphan daemons
    terminated = terminate_orphan_daemons(pid_path=TEST_PID_PATH)
    print(f"terminate_orphan_daemons returned: {terminated}")
    time.sleep(0.3)

    assert not is_pid_alive(proc.pid), f"Process {proc.pid} referenced by stale PID file was not terminated!"
    assert not os.path.exists(TEST_PID_PATH), "Stale PID file was not removed!"
    print("PASS: Stale PID file and referenced unlocked process terminated cleanly.")


def test_concurrency_refusal_exit_code_1():
    print("\n--- [CHALLENGE 5] Singleton Mutex & Exit Code 1 on Conflict ---")
    cleanup_test_file()

    # Start primary daemon
    p1 = subprocess.Popen(
        [sys.executable, "scripts/run_freshner_daemon.py", "--pid-file", TEST_PID_PATH, "--interval", "60", "--store", "noop_store"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    for _ in range(100):
        if is_daemon_locked(TEST_PID_PATH):
            break
        time.sleep(0.1)

    assert is_daemon_locked(TEST_PID_PATH), "p1 failed to lock"

    # Start second instance - must fail immediately with code 1
    t0 = time.time()
    p2 = subprocess.run(
        [sys.executable, "scripts/run_freshner_daemon.py", "--pid-file", TEST_PID_PATH, "--interval", "60", "--store", "noop_store"],
        capture_output=True,
        text=True
    )
    t1 = time.time()
    duration = t1 - t0

    print(f"Instance 2 exited in {duration:.2f}s with code: {p2.returncode}")
    print(f"Instance 2 output:\n{p2.stdout}{p2.stderr}")

    assert p2.returncode == 1, f"Expected returncode 1, got {p2.returncode}"
    assert "Another daemon instance is already active" in (p2.stdout + p2.stderr), "Missing expected refusal warning"
    assert str(p1.pid) in (p2.stdout + p2.stderr), f"Expected active PID {p1.pid} in refusal log"

    # Clean up p1
    terminate_pid(p1.pid)
    p1.wait(timeout=5)
    time.sleep(0.3)
    cleanup_test_file()
    print("PASS: Concurrency refusal exit code 1 verified.")


def test_high_concurrency_lock_race():
    print("\n--- [CHALLENGE 6] High Concurrency Lock Race (10 Concurrent Callers) ---")
    cleanup_test_file()

    results = []
    handles = []

    def try_lock(worker_id):
        acquired, handle, pid = acquire_daemon_lock(TEST_PID_PATH)
        results.append((worker_id, acquired, pid))
        if acquired:
            handles.append(handle)

    threads = [threading.Thread(target=try_lock, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    successes = [r for r in results if r[1] is True]
    failures = [r for r in results if r[1] is False]

    print(f"Race results: {len(successes)} succeeded, {len(failures)} failed")
    assert len(successes) == 1, f"Expected exactly 1 lock winner, got {len(successes)}"
    assert len(failures) == 9, f"Expected 9 lock losers, got {len(failures)}"

    # Release winner lock
    for h in handles:
        release_daemon_lock(h, TEST_PID_PATH)

    cleanup_test_file()
    print("PASS: High concurrency race strictly allowed exactly 1 winner.")


def test_rapid_acquire_release_stress():
    print("\n--- [CHALLENGE 7] Rapid 50x Acquire/Release Cycles ---")
    cleanup_test_file()

    for i in range(50):
        ok, handle, pid = acquire_daemon_lock(TEST_PID_PATH)
        assert ok, f"Cycle {i}: Failed to acquire lock"
        assert pid == os.getpid(), f"Cycle {i}: PID mismatch"
        active_pid = read_active_daemon_pid(TEST_PID_PATH)
        assert active_pid == os.getpid(), f"Cycle {i}: Read PID mismatch: {active_pid}"
        release_daemon_lock(handle, TEST_PID_PATH)
        assert not os.path.exists(TEST_PID_PATH), f"Cycle {i}: PID file should be removed"

    print("PASS: 50 sequential acquire/release cycles completed without error.")


def test_abrupt_crash_recovery():
    print("\n--- [CHALLENGE 8] Abrupt Process Death / Crash Recovery ---")
    cleanup_test_file()

    crash_script = """
import sys, time
from storage.daemon_lock import acquire_daemon_lock
ok, handle, pid = acquire_daemon_lock('{path}')
if ok:
    sys.stdout.write('LOCKED\\n')
    sys.stdout.flush()
    time.sleep(60)
""".replace("{path}", TEST_PID_PATH.replace("\\", "/"))

    p = subprocess.Popen(
        [sys.executable, "-c", crash_script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    line = p.stdout.readline()
    assert "LOCKED" in line, "Subprocess failed to lock"
    assert is_daemon_locked(TEST_PID_PATH), "Lock not held"
    crashed_pid = p.pid
    print(f"Process {crashed_pid} locked PID file. Now killing violently with taskkill /F...")

    # Kill violently (simulating power failure / SIGKILL / taskkill /F)
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/F", "/PID", str(crashed_pid)], capture_output=True)
    else:
        p.kill()
    p.wait()
    time.sleep(0.3)

    assert os.path.exists(TEST_PID_PATH), "File should still exist on abrupt crash"
    locked = is_daemon_locked(TEST_PID_PATH)
    print(f"Post-crash lock status: {locked}")
    assert not locked, "OS kernel failed to release byte lock after process termination!"

    # A new daemon should now be able to acquire lock immediately
    ok2, handle2, pid2 = acquire_daemon_lock(TEST_PID_PATH)
    assert ok2, "Failed to acquire lock after previous process crash!"
    assert pid2 == os.getpid(), "PID mismatch on re-acquisition"
    release_daemon_lock(handle2, TEST_PID_PATH)
    cleanup_test_file()
    print("PASS: Abrupt crash recovery verified. OS automatically freed lock.")


def test_corrupt_pid_file_handling():
    print("\n--- [CHALLENGE 9] Corrupt & Malformed PID File Handling ---")
    cleanup_test_file()

    test_cases = [
        "",                     # Empty file
        "     \n",             # Whitespace
        "not_a_number\n",      # Non-numeric string
        "-1234\n",             # Negative number
        "9999999999999999999\n",# Extremely large number
        "12345 67890\n",       # Multi-token
        "\x00\x00\x00\x00",    # Binary nulls
    ]

    for tc in test_cases:
        with open(TEST_PID_PATH, "wb") as f:
            f.write(tc.encode("utf-8") if isinstance(tc, str) else tc)
        
        pid = read_active_daemon_pid(TEST_PID_PATH)
        print(f"Input: {repr(tc)[:20]} -> read_active_daemon_pid: {pid}")
        ok, handle, active_pid = acquire_daemon_lock(TEST_PID_PATH)
        assert ok, f"acquire_daemon_lock failed on corrupt content: {repr(tc)}"
        assert active_pid == os.getpid()
        release_daemon_lock(handle, TEST_PID_PATH)

    cleanup_test_file()
    print("PASS: Corrupt & malformed PID files handled gracefully without exceptions.")


def test_simultaneous_daemon_launches():
    print("\n--- [CHALLENGE 10] Simultaneous Multi-Instance Launches (5 Competing Daemons) ---")
    sim_pid_path = os.path.join("storage", "test_simultaneous.pid")
    cleanup_test_file(sim_pid_path)

    # Launch 5 daemon instances at the exact same instant
    cmd = [
        sys.executable, "scripts/run_freshner_daemon.py",
        "--pid-file", sim_pid_path,
        "--interval", "60",
        "--store", "noop_store"
    ]

    procs = [
        subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for _ in range(5)
    ]
    pids = [p.pid for p in procs]
    print(f"Launched 5 simultaneous daemons with PIDs: {pids}")

    # Wait up to 10 seconds for initial settlement
    time.sleep(5)

    # Read output and return codes
    results = []
    for p in procs:
        poll = p.poll()
        if poll is not None:
            out, err = p.communicate()
            results.append({"pid": p.pid, "alive": False, "rc": poll, "output": (out + err).strip()})
        else:
            results.append({"pid": p.pid, "alive": True, "rc": None, "output": ""})

    print("\nSimultaneous launch results:")
    for r in results:
        print(f"PID {r['pid']}: alive={r['alive']}, rc={r['rc']}, output_len={len(r['output'])}, output={r['output'][:80]}")

    alive_procs = [r for r in results if r["alive"]]
    dead_procs = [r for r in results if not r["alive"]]

    print(f"\nSummary: {len(alive_procs)} alive, {len(dead_procs)} terminated")

    # Clean up any surviving processes
    for r in alive_procs:
        terminate_pid(r["pid"])
    cleanup_test_file(sim_pid_path)

    # Analyze failure modes:
    # Acceptance criteria requires:
    # 1. Exactly 1 daemon running
    # 2. All rejected instances exit with code 1 AND log the refusal warning
    empty_killed = [r for r in dead_procs if len(r["output"]) == 0 or "Another daemon instance is already active" not in r["output"]]
    if empty_killed:
        print(f"\n[FAILURE OBSERVED] {len(empty_killed)} losing processes were terminated abruptly without logging refusal message!")
        for ek in empty_killed:
            print(f"  -> PID {ek['pid']} died with rc={ek['rc']}, output='{ek['output']}'")
        return False
    else:
        print("\nAll rejected daemons cleanly logged refusal message.")
        return True


if __name__ == "__main__":
    print("=" * 70)
    print("STARTING EMPIRICAL ADVERSARIAL STRESS TEST SUITE FOR M1")
    print("=" * 70)
    
    test_orphan_termination_basic()
    test_active_daemon_preservation()
    test_stale_pid_dead_process()
    test_stale_pid_live_process()
    test_concurrency_refusal_exit_code_1()
    test_high_concurrency_lock_race()
    test_rapid_acquire_release_stress()
    test_abrupt_crash_recovery()
    test_corrupt_pid_file_handling()
    sim_ok = test_simultaneous_daemon_launches()

    print("\n" + "=" * 70)
    if sim_ok:
        print("ALL 10 ADVERSARIAL STRESS TESTS COMPLETED SUCCESSFULLY!")
    else:
        print("EMPIRICAL CHALLENGE CONFIRMED CRITICAL BUG: SIMULTANEOUS DAEMON LAUNCH ASSASSINATION RACE!")
    print("=" * 70)
