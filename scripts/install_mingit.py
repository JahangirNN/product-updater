import urllib.request
import json
import zipfile
import os
import sys

print("Checking latest MinGit release from GitHub...")
url = "https://api.github.com/repos/git-for-windows/git/releases/latest"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    
    mingit_asset = None
    for asset in data.get("assets", []):
        name = asset.get("name", "")
        if name.startswith("MinGit-") and "64-bit.zip" in name and "busybox" not in name.lower():
            mingit_asset = asset
            break
            
    if not mingit_asset:
        print("Asset not found in latest, trying fallback URL")
        download_url = "https://github.com/git-for-windows/git/releases/download/v2.47.1.windows.1/MinGit-2.47.1-64-bit.zip"
    else:
        download_url = mingit_asset.get("browser_download_url")
        print("Found MinGit asset:", mingit_asset.get("name"))
        
    dest_dir = r"C:\Users\Jahangir\AppData\Local\Programs\MinGit"
    os.makedirs(dest_dir, exist_ok=True)
    zip_path = os.path.join(dest_dir, "mingit.zip")
    
    print(f"Downloading from {download_url} to {zip_path}...")
    urllib.request.urlretrieve(download_url, zip_path)
    print("Download completed! File size:", os.path.getsize(zip_path))
    
    print(f"Extracting to {dest_dir}...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(dest_dir)
        
    print("MinGit extracted successfully!")
    git_exe = os.path.join(dest_dir, "cmd", "git.exe")
    print("git.exe path:", git_exe, "Exists:", os.path.exists(git_exe))
    
except Exception as e:
    print("Error:", e)
