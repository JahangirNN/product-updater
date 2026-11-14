import subprocess

GIT = r"c:\workspace\dropship-scraper-portable-20260905\tools\mingit\cmd\git.exe"
CWD = r"c:\workspace\dropship-scraper-portable-20260905\product-updater"

print("Running: git push origin main ...")
res = subprocess.run([GIT, "push", "origin", "main"], cwd=CWD, capture_output=True, text=True)
print("Return code:", res.returncode)
print("STDOUT:\n", res.stdout)
print("STDERR:\n", res.stderr)
