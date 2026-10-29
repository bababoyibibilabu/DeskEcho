import os
import sys
import json
import datetime
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

def run_cmd(cmd: list) -> str:
    print(f">> {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=str(ROOT_DIR), capture_output=True, text=True, encoding='utf-8')
    if res.returncode != 0:
        print(f"Error ({res.returncode}): {res.stderr.strip()}")
        sys.exit(res.returncode)
    return res.stdout.strip()

def release(new_version: str, title: str = "", changelog: list = None):
    new_version = new_version.strip().lstrip('v')
    today_str = datetime.date.today().isoformat()
    if not title:
        title = f"DeskEcho v{new_version} 正式发版"
    if not changelog:
        changelog = [
            f"DeskEcho v{new_version} 版本更新与系统稳定性增强",
            "持续优化对讲与会议切片检索体验"
        ]

    print(f"========================================")
    print(f"🚀 准备发版: DeskEcho v{new_version}")
    print(f"📅 发版日期: {today_str}")
    print(f"📋 标题: {title}")
    print(f"========================================")

    # 1. 更新 version.py
    version_py_path = ROOT_DIR / "version.py"
    version_py_content = f'''APP_VERSION = "{new_version}"
APP_NAME = "DeskEcho"
RELEASE_DATE = "{today_str}"
GITHUB_REPO = "bababoyibibilabu/DeskEcho"
VERSION_URL = f"https://raw.githubusercontent.com/{{GITHUB_REPO}}/main/version.json"
RELEASE_API_URL = f"https://api.github.com/repos/{{GITHUB_REPO}}/releases/latest"
'''
    with open(version_py_path, "w", encoding="utf-8") as f:
        f.write(version_py_content)
    print("✓ 已更新 version.py")

    # 2. 更新 version.json
    version_json_path = ROOT_DIR / "version.json"
    version_data = {
        "version": new_version,
        "release_date": today_str,
        "title": title,
        "changelog": changelog,
        "download_url": f"https://github.com/bababoyibibilabu/DeskEcho/archive/refs/tags/v{new_version}.zip",
        "min_version": "0.1.0"
    }
    with open(version_json_path, "w", encoding="utf-8") as f:
        json.dump(version_data, f, ensure_ascii=False, indent=2)
    print("✓ 已更新 version.json")

    # 3. Git Commit, Tag & Push
    tag_name = f"v{new_version}"
    run_cmd(["git", "add", "version.py", "version.json"])
    run_cmd(["git", "commit", "-m", f"chore(release): 发布正式版本 {tag_name}"])
    
    # 检查 tag 是否已存在，若存在先删除再重置
    existing_tags = run_cmd(["git", "tag", "-l", tag_name])
    if existing_tags:
        print(f"⚠️ Tag {tag_name} 已存在，正在更新...")
        run_cmd(["git", "tag", "-d", tag_name])
        run_cmd(["git", "push", "origin", f":refs/tags/{tag_name}"])

    run_cmd(["git", "tag", "-a", tag_name, "-m", f"Release {tag_name}: {title}"])
    print(f"✓ 已创建 Git Tag: {tag_name}")

    # 4. 推送到远端 GitHub
    print(">>> 正在推送代码与 Tag 至 GitHub 远端仓库...")
    run_cmd(["git", "push", "origin", "main"])
    run_cmd(["git", "push", "origin", tag_name])

    print(f"\n🎉 恭喜！DeskEcho {tag_name} 已成功发版并推送到 GitHub！")
    print(f"🔗 Release 地址: https://github.com/bababoyibibilabu/DeskEcho/releases/tag/{tag_name}")

if __name__ == "__main__":
    ver = sys.argv[1] if len(sys.argv) > 1 else "0.2.0"
    rel_title = sys.argv[2] if len(sys.argv) > 2 else ""
    release(ver, rel_title)
