import os
import json
import datetime

def check_freshness():
    # 1. Daemon PID & Process Check
    pid_file = "storage/daemon.pid"
    if os.path.exists(pid_file):
        try:
            with open(pid_file, "r", encoding="utf-8") as f:
                pid = f.read().strip()
            print(f"Daemon PID in lock file: {pid}")
        except Exception as e:
            print(f"Error reading daemon pid: {e}")

    # 2. Check freshner.log for latest cycle sweep counts
    freshner_log_path = "logs/freshner.log"
    if os.path.exists(freshner_log_path):
        with open(freshner_log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        print(f"Total lines in freshner.log: {len(lines)}")
        for s in ["coach", "jwpei", "michaelkors"]:
            matches = [l.strip() for l in lines if f"[{s.upper()}" in l]
            if matches:
                last_m = matches[-1]
                print(f"  [{s.upper()}] Recent log: {last_m}")

    # 3. Check sample products' last_verified_at
    print("\nSample Product last_verified_at inspection:")
    for store in ["coach", "jwpei", "michaelkors"]:
        pdir = os.path.join("storage/db", store, "products")
        if os.path.exists(pdir):
            files = [f for f in os.listdir(pdir) if f.endswith(".json")]
            if files:
                verified_times = []
                for fname in files[:20]:
                    with open(os.path.join(pdir, fname), "r", encoding="utf-8") as pf:
                        pdata = json.load(pf)
                    vt = pdata.get("last_verified_at")
                    if vt:
                        verified_times.append(vt)
                latest_vt = max(verified_times) if verified_times else "None"
                print(f"  [{store.upper()}] {len(files)} total products. Sample latest verified: {latest_vt}")

    # 4. Check delta_events.jsonl
    events_path = "storage/db/history/delta_events.jsonl"
    if os.path.exists(events_path):
        with open(events_path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
        bag_evts = []
        for l in lines:
            try:
                ev = json.loads(l)
                if ev.get("store") in ("coach", "jwpei", "michaelkors"):
                    bag_evts.append(ev)
            except Exception:
                pass
        print(f"\nDelta Events Queue: {len(lines)} total events, {len(bag_evts)} from bag stores.")
        if bag_evts:
            last = bag_evts[-1]
            print(f"Latest bag event: {last.get('timestamp')} | Store: {last.get('store')} | Title: {last.get('title')[:30]} | Price Chg: {last.get('price_changed')} | Stock Chg: {last.get('stock_changed')} | Synced: {not last.get('shopify_sync_pending')}")

if __name__ == "__main__":
    check_freshness()
