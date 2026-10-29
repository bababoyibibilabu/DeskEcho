import time
import json
from pathlib import Path

def do(act, out, **kwargs):
    tf = Path("C:/DeskEcho/trigger_action.json")
    rf = Path("C:/DeskEcho/action_result.json")
    if rf.exists():
        rf.unlink()
    payload = {"action": act, "output_path": out, **kwargs}
    tf.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    for _ in range(15):
        time.sleep(0.5)
        if rf.exists():
            return json.loads(rf.read_text(encoding="utf-8"))
    return None

if __name__ == "__main__":
    for t in ["light", "dark"]:
        print(f"Setting theme: {t}")
        do("set_theme", f"C:/DeskEcho/theme_{t}.png", theme=t)
        time.sleep(0.5)
        for p in [0, 1, 2, 4]:
            print(f"Switching to page {p} in {t}")
            res = do(f"switch_page_{p}", f"C:/DeskEcho/real_page{p}_{t}.png")
            print(f"Result: {res}")
            time.sleep(0.5)
    print("ALL_DONE")
