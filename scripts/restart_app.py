import os
import subprocess
import time

def restart():
    current_pid = os.getpid()
    print(f"[*] Current PID: {current_pid}")
    
    # Get all python PIDs
    out = subprocess.run(r'powershell -Command "Get-Process python -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id"', shell=True, capture_output=True, text=True)
    pids = [p.strip() for p in out.stdout.strip().split() if p.strip()]
    for p in pids:
        if p != str(current_pid):
            print(f"[*] Killing existing python process: {p}")
            subprocess.run(f"taskkill /F /PID {p}", shell=True, capture_output=True)
            
    time.sleep(1)
    
    # Launch main.py in background detached
    DETACHED_PROCESS = 0x00000008
    CREATE_NEW_PROCESS_GROUP = 0x00000200
    p = subprocess.Popen(
        [r"D:\anaconda3\envs\deskecho\python.exe", "main.py"],
        cwd=r"C:\DeskEcho",
        creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
        close_fds=True
    )
    print(f"[+] DeskEcho spawned detached with PID: {p.pid}")
    time.sleep(2)

if __name__ == "__main__":
    restart()
