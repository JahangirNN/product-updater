import urllib.request
import json

url = "https://api.github.com/repos/JahangirNN/product-updater/actions/runs"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        latest = data["workflow_runs"][0]
        run_id = latest["id"]
        status = latest["status"]
        conclusion = latest["conclusion"]
        print(f"Run #{latest['run_number']} (ID: {run_id}): {status} / {conclusion}")
        
        # Check jobs
        jobs_url = f"https://api.github.com/repos/JahangirNN/product-updater/actions/runs/{run_id}/jobs"
        req_jobs = urllib.request.Request(jobs_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req_jobs) as resp_jobs:
            jobs_data = json.loads(resp_jobs.read().decode())
            for job in jobs_data.get("jobs", []):
                print(f"  Job: {job['name']} - {job['status']} ({job.get('conclusion')})")
                for s in job.get("steps", []):
                    print(f"    Step: {s['name']} - {s['status']} ({s.get('conclusion')})")
except Exception as e:
    print("Error:", e)
