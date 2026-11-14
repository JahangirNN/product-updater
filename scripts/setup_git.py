import os
import sys
import shutil
import urllib.request
import zipfile
import subprocess

CANDIDATES = [
    r"C:\Program Files\Git\cmd\git.exe",
    r"C:\Program Files\Git\bin\git.exe",
    r"C:\Program Files (x86)\Git\cmd\git.exe",
    r"C:\Users\Jahangir\AppData\Local\Programs\Git\cmd\git.exe",
    r"C:\tools\mingit\cmd\git.exe",
    r"c:\workspace\dropship-scraper-portable-20260905\tools\mingit\cmd\git.exe",
    r"c:\workspace\dropship-scraper-portable-20260905\tools\mingit\bin\git.exe"
]

def find_git():
    if shutil.which("git"):
        return shutil.which("git")
    for path in CANDIDATES:
        if os.path.exists(path):
            return path
    # Search AppData
    appdata = os.environ.get("LOCALAPPDATA", "")
    if appdata:
        gh_desktop = os.path.join(appdata, "GitHubDesktop")
        if os.path.exists(gh_desktop):
            for root, dirs, files in os.walk(gh_desktop):
                if "git.exe" in files:
                    return os.path.join(root, "git.exe")
    return None

def install_mingit():
    target_dir = r"c:\workspace\dropship-scraper-portable-20260905\tools\mingit"
    os.makedirs(target_dir, exist_ok=True)
    zip_path = r"c:\workspace\dropship-scraper-portable-20260905\tools\mingit.zip"
    
    # Official MinGit release URL (portable, standalone, ~30-40MB)
    url = "https://github.com/git-for-windows/git/releases/download/v2.47.1.windows.1/MinGit-2.47.1-64-bit.zip"
    print(f"Downloading MinGit from {url} to {zip_path}...")
    headers = {"User-Agent": "Mozilla/5.0"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp, open(zip_path, "wb") as out_file:
        shutil.copyfileobj(resp, out_file)
    
    print(f"Downloaded. Size: {os.path.getsize(zip_path)} bytes. Extracting...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(target_dir)
    print("MinGit extracted successfully.")
    
    git_exe = os.path.join(target_dir, "cmd", "git.exe")
    if not os.path.exists(git_exe):
        git_exe = os.path.join(target_dir, "bin", "git.exe")
    return git_exe

def main():
    git = find_git()
    if git:
        print(f"Found existing Git: {git}")
    else:
        print("Git not found on system. Installing MinGit...")
        git = install_mingit()
    
    # Verify git
    print(f"Verifying git executable: {git}")
    res = subprocess.run([git, "--version"], capture_output=True, text=True)
    print(f"Git version output: {res.stdout.strip()}")
    
    # Write git wrapper or path config
    git_bat = r"c:\workspace\dropship-scraper-portable-20260905\tools\git.bat"
    with open(git_bat, "w") as f:
        f.write(f'@"{git}" %*\n')
    print(f"Created git wrapper at {git_bat}")

if __name__ == "__main__":
    main()
