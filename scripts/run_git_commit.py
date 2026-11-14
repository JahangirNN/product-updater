import subprocess

GIT = r"c:\workspace\dropship-scraper-portable-20260905\tools\mingit\cmd\git.exe"
CWD = r"c:\workspace\dropship-scraper-portable-20260905\product-updater"

msg = "fix(viewer): fix variant prices, price ranges and dynamic swatch selection in catalog viewer"

res = subprocess.run([GIT, "commit", "-m", msg], cwd=CWD, capture_output=True, text=True)
print("Return code:", res.returncode)
print("STDOUT:\n", res.stdout)
print("STDERR:\n", res.stderr)
