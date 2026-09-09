"""
Catalog Viewer Publisher & Deployment CLI
Exports the latest database, rebuilds frontend assets, and commits/pushes to GitHub.
Pure functions, zero classes (ADR 0004, ADR 0005).
"""
import os
import sys
import subprocess
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from typing import Tuple
from scripts.export_viewer_data import export_catalog


def run_cmd(cmd: str, cwd: str = None) -> Tuple[int, str, str]:
    """Execute shell command and return stdout/stderr."""
    print(f"  > {cmd}")
    proc = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True, encoding='utf-8')
    if proc.returncode != 0 and "nothing to commit" not in proc.stdout and "nothing to commit" not in proc.stderr:
        print(f"[WARN] Command output: {proc.stdout.strip()} {proc.stderr.strip()}")
    return proc.returncode, proc.stdout, proc.stderr


def publish_viewer(auto_push: bool = True):
    print("=" * 65)
    print("CATALOG VIEWER AUTOMATED EXPORT & DEPLOYMENT")
    print("=" * 65)

    # 1. Export fresh database snapshot to frontend/public/data
    print("\n[1/4] Exporting fresh catalog JSON from storage/db/...")
    count, target_file = export_catalog()
    print(f"      Exported {count} products successfully.")

    # 2. Build frontend production assets
    print("\n[2/4] Building Vite production bundle...")
    frontend_dir = os.path.join(os.getcwd(), "frontend")
    code, stdout, stderr = run_cmd("npm run build", cwd=frontend_dir)
    if code != 0:
        print(f"[ERROR] Frontend build failed: {stderr}")
        return False
    print("      Vite build complete: frontend/dist/ generated.")

    # 3. Git status & stage
    print("\n[3/4] Staging catalog data and frontend changes...")
    run_cmd("git add frontend/ storage/db/ scripts/")

    commit_msg = f"chore(catalog): sync live product catalog [{count} items] ({time.strftime('%Y-%m-%d %H:%M')})"
    code, stdout, stderr = run_cmd(f'git commit -m "{commit_msg}"')
    if "nothing to commit" in stdout or "nothing to commit" in stderr:
        print("      No changes detected since last export.")
    else:
        print(f"      Committed: {commit_msg}")

    # 4. Push to remote
    if auto_push:
        print("\n[4/4] Pushing to remote repository...")
        code, stdout, stderr = run_cmd("git push origin main")
        if code == 0:
            print("      Pushed successfully to origin/main.")
            print("\nGitHub Actions will automatically deploy to GitHub Pages:")
            print("  https://jahangirnn.github.io/product-updater/")
        else:
            print(f"      [NOTE] Push skipped or requires remote setup: {stderr.strip()}")

    print("\n" + "=" * 65)
    print("PUBLISH COMPLETE")
    print("=" * 65)
    return True


if __name__ == "__main__":
    publish_viewer(auto_push=False)  # default to staging, caller can pass flag
