import subprocess
import os

GIT = r"C:\Users\Jahangir\AppData\Local\Programs\MinGit\cmd\git.exe"
CWD = r"C:\workspace\dropship-scraper-portable-20260905\product-updater"

print("Configuring git user...")
subprocess.run([GIT, "config", "user.name", "JahangirNN"], cwd=CWD)
subprocess.run([GIT, "config", "user.email", "jahangirnn@users.noreply.github.com"], cwd=CWD)

print("Staging all changes in product-updater...")
subprocess.run([GIT, "add", "-A"], cwd=CWD, check=True)

print("Checking status before commit...")
status = subprocess.run([GIT, "status", "--short"], cwd=CWD, capture_output=True, text=True)
print("Staged items preview:", len(status.stdout.strip().split("\n")), "files staged.")

print("Committing...")
commit_msg = (
    "feat: catalog freshener daemon, zero-image enforcement, universal pricing engine, "
    "and production deployment config"
)
res = subprocess.run([GIT, "commit", "-m", commit_msg], cwd=CWD, capture_output=True, text=True)
print("Commit return code:", res.returncode)
print("Commit output:\n", res.stdout[:500])
if res.stderr:
    print("Commit stderr:\n", res.stderr[:500])
