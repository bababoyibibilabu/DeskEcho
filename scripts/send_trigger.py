import json
import time
from pathlib import Path

def trigger(action="inspect_trash", output_path="C:/DeskEcho/real_trash_window.png"):
    trigger_file = Path("C:/DeskEcho/trigger_action.json")
    result_file = Path("C:/DeskEcho/action_result.json")
    
    if result_file.exists():
        result_file.unlink()
        
    payload = {
        "action": action,
        "output_path": output_path
    }
    trigger_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"[*] Sent action: {action}")
    
    for _ in range(15):
        time.sleep(1)
        if result_file.exists():
            res = json.loads(result_file.read_text(encoding='utf-8'))
            print("[+] Action completed with result:")
            print(json.dumps(res, ensure_ascii=False, indent=2))
            return True
            
    print("[-] Timeout waiting for action_result.json")
    return False

if __name__ == "__main__":
    import sys
    action = sys.argv[1] if len(sys.argv) > 1 else "inspect_trash"
    out_path = sys.argv[2] if len(sys.argv) > 2 else "C:/DeskEcho/real_trash_window.png"
    extra = {}
    for arg in sys.argv[3:]:
        if "=" in arg:
            k, v = arg.split("=", 1)
            extra[k] = v
            
    trigger_file = Path("C:/DeskEcho/trigger_action.json")
    result_file = Path("C:/DeskEcho/action_result.json")
    
    if result_file.exists():
        result_file.unlink()
        
    payload = {
        "action": action,
        "output_path": out_path,
        **extra
    }
    trigger_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"[*] Sent action: {action} with {extra}")
    
    for _ in range(15):
        time.sleep(1)
        if result_file.exists():
            res = json.loads(result_file.read_text(encoding='utf-8'))
            print("[+] Action completed with result:")
            print(json.dumps(res, ensure_ascii=False, indent=2))
            sys.exit(0)
            
    print("[-] Timeout waiting for action_result.json")
    sys.exit(1)
