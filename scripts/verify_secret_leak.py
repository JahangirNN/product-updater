import subprocess

GIT = r"C:\Users\Jahangir\AppData\Local\Programs\MinGit\cmd\git.exe"
CWD = r"C:\workspace\dropship-scraper-portable-20260905\product-updater"

res = subprocess.run([GIT, "status", "--porcelain"], cwd=CWD, capture_output=True, text=True)
for line in res.stdout.strip().split("\n"):
    if ".env" in line or "pid" in line or "log" in line:
        print("ALERT:", line)

print("Scan complete. If no ALERT above, all secrets and runtime files are cleanly ignored!")
