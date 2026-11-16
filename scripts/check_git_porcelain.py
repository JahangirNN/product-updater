import subprocess
import os

GIT = r"C:\Users\Jahangir\AppData\Local\Programs\MinGit\cmd\git.exe"
CWD = r"C:\workspace\dropship-scraper-portable-20260905\product-updater"

res = subprocess.run([GIT, "status", "--porcelain"], cwd=CWD, capture_output=True, text=True)
lines = res.stdout.strip().split("\n")
print(f"Total modified/untracked files in product-updater: {len(lines)}")

modified = [l for l in lines if l.startswith(" M") or l.startswith("M ")]
untracked = [l for l in lines if l.startswith("??")]
deleted = [l for l in lines if l.startswith(" D") or l.startswith("D ")]

print(f"Modified: {len(modified)}")
print(f"Untracked: {len(untracked)}")
print(f"Deleted: {len(deleted)}")

print("\nSample untracked:")
for u in untracked[:15]:
    print(" ", u)
