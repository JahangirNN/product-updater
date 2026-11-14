import os
import subprocess

GIT = r"c:\workspace\dropship-scraper-portable-20260905\tools\mingit\cmd\git.exe"
CWD = r"c:\workspace\dropship-scraper-portable-20260905\product-updater"

env = os.environ.copy()
env["GIT_TERMINAL_PROMPT"] = "0"

res = subprocess.run([GIT, "push", "--dry-run", "origin", "main"], cwd=CWD, env=env, capture_output=True, text=True)
print("Return code:", res.returncode)
print("STDOUT:\n", res.stdout)
print("STDERR:\n", res.stderr)
