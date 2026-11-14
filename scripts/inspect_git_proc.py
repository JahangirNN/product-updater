import subprocess

out = subprocess.check_output(['powershell', '-Command', "Get-Process -Name git | Select-Object Id, Path"], text=True)
print(out)

