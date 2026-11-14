import json

with open(r'C:\Users\Jahangir\.gemini\antigravity\brain\5a5cc45f-5127-4b1a-a581-3e2bc159c5fb\.system_generated\logs\transcript.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        obj = json.loads(line)
        idx = obj.get('step_index')
        if idx in [5821, 5822, 5823]:
            print(f"=== STEP {idx} ===")
            print(json.dumps(obj, indent=2)[:1000])
