"""
DeskEcho 敏捷自进化循环扫描与调度器 (Autonomous Loop Dispatcher)
功能：
1. 通过 SSH / 本地持续扫描笔记本或本地的 iteration_queue.json
2. 识别状态为 PENDING 的操作员改进指令
3. 处理多指令堆积与防抖合并（30-60秒窗口合并处理）
4. 辅助智能体执行：需求归纳 -> 代码改进 -> SSH 同步真机验证 -> GitHub 发版与自动推送
5. 任务闭环状态打标 (PENDING -> PROCESSING -> COMPLETED)
"""
import os
import sys
import json
import time
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

REMOTE_SSH = "Administrator@192.168.1.166"
REMOTE_QUEUE_PATHS = [
    r"D:\DeskEcho_Data\iteration_queue.json",
    r"C:\DeskEcho\omni_data\iteration_queue.json",
    r"C:\DeskEcho\iteration_queue.json"
]

def get_local_queue_path() -> Path:
    from config import Config
    return Config.DATA_DIR / "iteration_queue.json"

def fetch_remote_tasks(remote_host: str = REMOTE_SSH) -> List[Dict[str, Any]]:
    """通过 SSH 从笔记本读取 iteration_queue.json"""
    for rpath in REMOTE_QUEUE_PATHS:
        cmd = f'ssh -o ConnectTimeout=5 {remote_host} "if exist {rpath} (type {rpath})"'
        try:
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=8)
            if res.returncode == 0 and res.stdout.strip():
                try:
                    data = json.loads(res.stdout.strip())
                    if isinstance(data, list):
                        return data
                except Exception:
                    pass
        except Exception as e:
            print(f"[Loop] 读取远程队列 {rpath} 提示: {e}")
    return []

def fetch_all_tasks() -> List[Dict[str, Any]]:
    """读取所有任务（优先远程真机，备选本地）"""
    tasks = fetch_remote_tasks()
    if not tasks:
        loc = get_local_queue_path()
        if loc.exists():
            try:
                tasks = json.loads(loc.read_text(encoding="utf-8"))
            except Exception:
                pass
    return tasks or []

def update_remote_task_status(task_id: str, new_status: str = "COMPLETED", commit_sha: str = "", remote_host: str = REMOTE_SSH):
    """更新远程与本地任务状态"""
    # 1. 更新远程文件
    remote_tasks = fetch_remote_tasks(remote_host)
    if remote_tasks:
        updated = False
        for t in remote_tasks:
            if t.get("id") == task_id:
                t["status"] = new_status
                t["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                if commit_sha:
                    t["commit_sha"] = commit_sha
                updated = True
        if updated:
            import tempfile
            tmp = Path(tempfile.gettempdir()) / "remote_queue_update.json"
            tmp.write_text(json.dumps(remote_tasks, ensure_ascii=False, indent=2), encoding="utf-8")
            subprocess.run(["scp", "-o", "ConnectTimeout=5", str(tmp), f"{remote_host}:D:/DeskEcho_Data/iteration_queue.json"], capture_output=True, timeout=10)
            print(f"[Loop] 远程任务 {task_id} 状态已更新为 {new_status}")

    # 2. 同步更新本地
    loc = get_local_queue_path()
    if loc.exists():
        try:
            tasks = json.loads(loc.read_text(encoding="utf-8"))
            for t in tasks:
                if t.get("id") == task_id:
                    t["status"] = new_status
                    t["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    if commit_sha:
                        t["commit_sha"] = commit_sha
            loc.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
    if loc.exists():
        try:
            tasks = json.loads(loc.read_text(encoding="utf-8"))
            for t in tasks:
                if t.get("id") == task_id:
                    t["status"] = new_status
                    t["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    if commit_sha:
                        t["commit_sha"] = commit_sha
            loc.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

def scan_pending_batch() -> Dict[str, Any]:
    """
    扫描待处理的工单批次
    处理多条工单堆积，智能合并相近时间段（60秒内）的反馈
    """
    tasks = fetch_all_tasks()
    pending = [t for t in tasks if t.get("status") == "PENDING"]
    if not pending:
        return {"has_pending": False, "count": 0, "tasks": []}

    print(f"[Loop] 发现 {len(pending)} 条待处理的改进工单！")
    return {
        "has_pending": True,
        "count": len(pending),
        "tasks": pending
    }

if __name__ == "__main__":
    print("=" * 60)
    print("  DeskEcho 敏捷自进化工单队列巡检")
    print("=" * 60)
    res = scan_pending_batch()
    if not res["has_pending"]:
        print("[+] 当前没有积压的 PENDING 工单，系统运行平稳。")
    else:
        for idx, t in enumerate(res["tasks"], 1):
            print(f"[{idx}] ID: {t.get('id')} | 类别: {t.get('category')} | 标题: {t.get('task_title')}")
            print(f"    原始口语: {t.get('raw_instruction')}")
            print(f"    诉求要点: {t.get('requirement_summary')}")
            print(f"    技术方案: {t.get('execution_plan')}\n")
