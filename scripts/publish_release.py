import os
import sys
import json
import subprocess
import requests
from pathlib import Path

def get_github_token():
    p = subprocess.Popen(['git', 'credential', 'fill'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, _ = p.communicate(input='protocol=https\nhost=github.com\n\n')
    token = None
    for line in out.splitlines():
        if line.startswith('password='):
            token = line.split('=', 1)[1]
    return token

def main():
    root = Path(__file__).resolve().parent.parent
    dist_exe = root / "dist" / "DeskEcho.exe"
    if not dist_exe.exists():
        print(f"[ERROR] dist/DeskEcho.exe not found at {dist_exe}")
        sys.exit(1)

    ver_file = root / "version.json"
    with open(ver_file, 'r', encoding='utf-8') as f:
        ver_info = json.load(f)

    tag = f"v{ver_info['version']}"
    title = ver_info.get("title", f"DeskEcho {tag}")
    changelog_lines = ver_info.get("changelog", [])
    body = "## 更新特性与改进说明\n" + "\n".join(f"- {c}" for c in changelog_lines)
    body += f"\n\n**发版规格**：单一 Windows EXE 独立可执行程序 (`DeskEcho.exe`，免安装运行)\n"

    token = get_github_token()
    if not token:
        print("[ERROR] Cannot get GitHub token from git credential manager.")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    owner = "bababoyibibilabu"
    repo = "DeskEcho"

    # 1. 检查或创建 Release
    print(f"[*] 检查 GitHub Release {tag}...", flush=True)
    rel_url = f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{tag}"
    r = requests.get(rel_url, headers=headers, timeout=30)
    
    release_id = None
    if r.status_code == 200:
        release_id = r.json().get("id")
        print(f"[*] 找到已有 Release {tag} (ID: {release_id})", flush=True)
    else:
        print(f"[*] 正在创建 GitHub Release {tag}...", flush=True)
        create_url = f"https://api.github.com/repos/{owner}/{repo}/releases"
        payload = {
            "tag_name": tag,
            "target_commitish": "main",
            "name": title,
            "body": body,
            "draft": False,
            "prerelease": False
        }
        cr = requests.post(create_url, headers=headers, json=payload, timeout=30)
        if cr.status_code in (200, 201):
            release_id = cr.json().get("id")
            print(f"[+] 成功创建 GitHub Release {tag} (ID: {release_id})", flush=True)
        else:
            print(f"[ERROR] 创建 Release 失败: {cr.status_code} - {cr.text}", flush=True)
            sys.exit(1)

    # 2. 上传 DeskEcho.exe 资产
    upload_url = f"https://uploads.github.com/repos/{owner}/{repo}/releases/{release_id}/assets?name=DeskEcho.exe"
    
    # 检查是否已存在同名资产
    assets_url = f"https://api.github.com/repos/{owner}/{repo}/releases/{release_id}/assets"
    ar = requests.get(assets_url, headers=headers, timeout=30)
    if ar.status_code == 200:
        for asset in ar.json():
            if asset.get("name") == "DeskEcho.exe":
                print(f"[*] 发现已有同名资产 {asset.get('name')} (ID: {asset.get('id')})，正在删除旧资产...", flush=True)
                del_url = f"https://api.github.com/repos/{owner}/{repo}/releases/assets/{asset.get('id')}"
                requests.delete(del_url, headers=headers, timeout=30)
                import time
                time.sleep(2)

    print(f"[*] 正在上传 {dist_exe.name} ({dist_exe.stat().st_size / (1024*1024):.1f} MB) 至 GitHub Release...", flush=True)
    with open(dist_exe, "rb") as f:
        up_headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/octet-stream"
        }
        ur = requests.post(upload_url, headers=up_headers, data=f, timeout=300)
        if ur.status_code in (200, 201):
            print(f"[SUCCESS] 成功上传发布资产 DeskEcho.exe！下载链接: {ur.json().get('browser_download_url')}", flush=True)
        else:
            print(f"[ERROR] 上传发布资产失败: {ur.status_code} - {ur.text}", flush=True)
            sys.exit(1)

if __name__ == "__main__":
    main()
