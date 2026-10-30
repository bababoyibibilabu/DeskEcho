# -*- coding: utf-8 -*-
"""
DeskEcho Autonomous Queue Watcher
Continuously monitors remote test machine and local queues for any PENDING tasks.
As soon as a PENDING task is detected, it prints details and exits (which immediately wakes up Antigravity).
"""
import sys
import time
import json
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.iteration_daemon import fetch_all_tasks

def main():
    print("[Watcher] Started watching for PENDING tasks on remote test machine...")
    sys.stdout.flush()
    max_duration = 3600  # 1 hour max per watcher task
    start_time = time.time()
    
    while time.time() - start_time < max_duration:
        try:
            tasks = fetch_all_tasks()
            pending = [t for t in tasks if t.get("status") == "PENDING"]
            if pending:
                print(f"[!] DETECTED {len(pending)} PENDING TASK(S)!")
                print(json.dumps(pending, ensure_ascii=False, indent=2))
                sys.stdout.flush()
                return 0
        except Exception as e:
            print(f"[Watcher] Error checking tasks: {e}")
            sys.stdout.flush()
        
        time.sleep(3)
    
    print("[Watcher] Reached timeout (1 hour), exiting.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
