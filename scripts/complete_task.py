import json
import time
from pathlib import Path

p = Path("D:/DeskEcho_Data/iteration_queue.json")
if not p.exists():
    p = Path("C:/DeskEcho/iteration_queue.json")

if p.exists():
    data = json.loads(p.read_text(encoding="utf-8"))
    for t in data:
        if t.get("id") == "REQ-20261103170537-A254":
            t["status"] = "COMPLETED"
            t["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            t["commit_sha"] = "v0.2.22"
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Remote task status updated to COMPLETED successfully!")
else:
    print("Queue file not found!")
