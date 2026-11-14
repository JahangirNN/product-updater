import json
import subprocess
import re

# Read token from step 5822 in transcript
token = None
with open(r'C:\Users\Jahangir\.gemini\antigravity\brain\5a5cc45f-5127-4b1a-a581-3e2bc159c5fb\.system_generated\logs\transcript.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        obj = json.loads(line)
        if obj.get('step_index') == 5822:
            content = str(obj)
            m = re.search(r'https://(ghp_[A-Za-z0-9]+)@github\.com', content)
            if m:
                token = m.group(1)
                break

if not token:
    print("Error: Could not locate token in step 5822")
    exit(1)

print(f"Located token: ghp_...{token[-4:]}")

GIT = r"c:\workspace\dropship-scraper-portable-20260905\tools\mingit\cmd\git.exe"
CWD = r"c:\workspace\dropship-scraper-portable-20260905\product-updater"

remote_auth_url = f"https://{token}@github.com/JahangirNN/product-updater.git"

print("Pushing to origin main with auth...")
res = subprocess.run(
    [GIT, "-c", "credential.helper=", "push", remote_auth_url, "main"],
    cwd=CWD,
    capture_output=True,
    text=True
)

print("Return code:", res.returncode)
print("STDOUT:\n", res.stdout)
print("STDERR:\n", res.stderr)
