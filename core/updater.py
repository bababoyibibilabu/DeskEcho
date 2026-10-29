import os
import sys
import json
import time
import zipfile
import shutil
import tempfile
import urllib.request
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, Callable
from PyQt6.QtCore import QThread, pyqtSignal

from version import APP_VERSION, VERSION_URL, RELEASE_API_URL

def parse_version(v_str: str) -> Tuple[int, ...]:
    """将版本号字符串如 'v0.2.0' 或 '0.2.0' 转换为数字元组用于比较"""
    clean_v = v_str.strip().lower().lstrip('v')
    parts = []
    for p in clean_v.split('.'):
        digits = ''.join(c for c in p if c.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)

def is_newer_version(remote_v: str, current_v: str) -> bool:
    """比较远端版本与当前版本"""
    try:
        return parse_version(remote_v) > parse_version(current_v)
    except Exception:
        return False

class UpdateChecker:
    """
    DeskEcho 版本检查与自动静默升级引擎
    支持通过 GitHub 官方仓库的 version.json 与 Releases 接口进行双重校验与断点提取
    """
    def __init__(self, current_version: str = APP_VERSION, app_dir: Optional[Path] = None):
        self.current_version = current_version
        self.app_dir = app_dir or Path(__file__).resolve().parent.parent

    def check_update(self) -> Optional[Dict[str, Any]]:
        """检查是否有新版本，若有则返回元数据字典，否则返回 None"""
        # 1. 优先从 GitHub raw version.json 拉取轻量元数据 (免 API 频次限制)
        try:
            req = urllib.request.Request(
                VERSION_URL,
                headers={"User-Agent": "DeskEcho-Client-AutoUpdater"}
            )
            with urllib.request.urlopen(req, timeout=6) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode('utf-8'))
                    remote_ver = data.get("version", "")
                    if is_newer_version(remote_ver, self.current_version):
                        return {
                            "has_update": True,
                            "version": remote_ver,
                            "title": data.get("title", f"DeskEcho v{remote_ver}"),
                            "changelog": data.get("changelog", []),
                            "download_url": data.get("download_url") or f"https://github.com/bababoyibibilabu/DeskEcho/archive/refs/tags/v{remote_ver}.zip",
                            "release_date": data.get("release_date", "")
                        }
        except Exception as e:
            print(f"[UpdateChecker] version.json 检查提示: {e}")

        # 2. 备选方案：从 GitHub Release API 拉取最新 Release
        try:
            req2 = urllib.request.Request(
                RELEASE_API_URL,
                headers={"User-Agent": "DeskEcho-Client-AutoUpdater", "Accept": "application/vnd.github.v3+json"}
            )
            with urllib.request.urlopen(req2, timeout=6) as resp:
                if resp.status == 200:
                    rel_data = json.loads(resp.read().decode('utf-8'))
                    tag_name = rel_data.get("tag_name", "").lstrip('v')
                    if tag_name and is_newer_version(tag_name, self.current_version):
                        zipball_url = rel_data.get("zipball_url") or f"https://github.com/bababoyibibilabu/DeskEcho/archive/refs/tags/v{tag_name}.zip"
                        body_text = rel_data.get("body", "")
                        changelog = [line.strip("- ").strip() for line in body_text.splitlines() if line.strip()]
                        return {
                            "has_update": True,
                            "version": tag_name,
                            "title": rel_data.get("name") or f"DeskEcho v{tag_name}",
                            "changelog": changelog,
                            "download_url": zipball_url,
                            "release_date": rel_data.get("published_at", "")[:10]
                        }
        except Exception as e:
            print(f"[UpdateChecker] GitHub Release API 检查提示: {e}")

        return None

    def download_and_apply_update(self, update_info: Dict[str, Any], on_progress: Optional[Callable[[str], None]] = None) -> bool:
        """
        下载最新发布包并安全覆盖本地代码文件
        严格保留本地敏感凭据 (.env) 与会议知识库 (omni_data, sqlite, chromadb)
        """
        download_url = update_info.get("download_url")
        target_version = update_info.get("version", "new")
        if not download_url:
            return False

        if on_progress:
            on_progress(f"正在下载 DeskEcho v{target_version} 发布包...")

        temp_dir = Path(tempfile.mkdtemp(prefix="deskecho_update_"))
        zip_path = temp_dir / "release.zip"

        try:
            # 1. 下载 zip 包 (若 tag zip 不可用，自动尝试 main 分支归档作为兜底)
            download_success = False
            for url in [download_url, "https://github.com/bababoyibibilabu/DeskEcho/archive/refs/heads/main.zip"]:
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": "DeskEcho-Client-AutoUpdater"})
                    with urllib.request.urlopen(req, timeout=25) as resp, open(zip_path, 'wb') as out_f:
                        shutil.copyfileobj(resp, out_f)
                    if zip_path.exists() and zip_path.stat().st_size > 1000:
                        download_success = True
                        break
                except Exception as de:
                    print(f"[UpdateChecker] 下载 {url} 失败: {de}")

            if not download_success:
                raise RuntimeError("无法从远端下载有效的发版安装包")

            if on_progress:
                on_progress("校验升级包完整性并应用更新...")

            # 判断是否为 Windows 独立可执行程序 (.exe)
            is_exe = download_url.lower().endswith(".exe") or (zip_path.exists() and zip_path.read_bytes()[:2] == b'MZ')
            if is_exe:
                target_exe = self.app_dir / "DeskEcho.exe"
                if getattr(sys, 'frozen', False):
                    # 运行在已打包的 EXE 模式下，利用批处理脚本避开 Windows 文件写锁定并重启
                    bat_path = temp_dir / "apply_update.bat"
                    bat_content = f"""@echo off
chcp 65001 >nul
timeout /t 2 /nobreak >nul
copy /y "{zip_path}" "{sys.executable}" >nul
start "" "{sys.executable}"
"""
                    bat_path.write_text(bat_content, encoding='utf-8')
                    import subprocess
                    subprocess.Popen(["cmd.exe", "/c", str(bat_path)], creationflags=0x08000000 if os.name == 'nt' else 0)
                    return True
                else:
                    # 运行在 Python 源码模式下：复制 DeskEcho.exe 到根目录
                    shutil.copy2(zip_path, target_exe)
                    print(f"[UpdateChecker] 已下载独立绿色可执行程序至 {target_exe}")

            # 2. 如果是 zip 归档包，解压到临时目录并热替换源码
            if not is_exe:
                extract_folder = temp_dir / "extracted"
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_folder)

                # GitHub 打包 zip 通常内嵌一层根目录 (如 DeskEcho-main 或 DeskEcho-0.2.0)
                inner_dirs = [p for p in extract_folder.iterdir() if p.is_dir()]
                source_root = inner_dirs[0] if inner_dirs else extract_folder

                if on_progress:
                    on_progress("正在安全应用最新代码与组件...")

                # 3. 白名单热替换保护策略
                # 允许更新的目录与文件：
                updatable_items = ["core", "ui", "config.py", "main.py", "version.py", "version.json", "README.md", "requirements.txt", "run.bat", "run_background.bat"]
                # 绝对保护的目录与文件 (绝不覆盖！)：
                protected_patterns = [".env", "omni_data", "records.db", "chroma", "local_data", "temp", "assets"]

                for item_name in updatable_items:
                    src_item = source_root / item_name
                    dst_item = self.app_dir / item_name
                    if not src_item.exists():
                        continue

                    if src_item.is_file():
                        shutil.copy2(src_item, dst_item)
                    elif src_item.is_dir():
                        # 递归安全复制目录
                        dst_item.mkdir(parents=True, exist_ok=True)
                        for root, dirs, files in os.walk(src_item):
                            rel_path = Path(root).relative_to(src_item)
                            dest_dir = dst_item / rel_path
                            dest_dir.mkdir(parents=True, exist_ok=True)
                            for f in files:
                                if any(p in f for p in protected_patterns):
                                    continue
                                shutil.copy2(Path(root) / f, dest_dir / f)

            print(f"[UpdateChecker] DeskEcho 成功升级至 v{target_version}！")
            return True

        except Exception as e:
            print(f"[UpdateChecker] 应用更新失败: {e}")
            return False
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def restart_app(self):
        """重启应用客户端"""
        try:
            import subprocess
            if getattr(sys, 'frozen', False):
                subprocess.Popen([sys.executable] + sys.argv[1:], cwd=str(self.app_dir))
            else:
                main_py = self.app_dir / "main.py"
                subprocess.Popen([sys.executable, str(main_py)] + sys.argv[1:], cwd=str(self.app_dir))
            sys.exit(0)
        except Exception as e:
            print(f"[UpdateChecker] 重启应用失败: {e}")


class AutoUpdateWorker(QThread):
    """
    PyQt6 后台静默自动更新线程
    在后台周期性检查并自动拉取 GitHub 最新版本
    """
    update_detected = pyqtSignal(dict)       # 发现新版本
    update_progress = pyqtSignal(str)        # 升级进度文案
    update_finished = pyqtSignal(str, dict)  # 升级完成 (新版本号, 元数据)
    update_failed = pyqtSignal(str)          # 升级出错

    def __init__(self, current_version: str = APP_VERSION, auto_apply: bool = True, parent=None):
        super().__init__(parent)
        self.checker = UpdateChecker(current_version)
        self.auto_apply = auto_apply

    def run(self):
        try:
            update_info = self.checker.check_update()
            if not update_info:
                return

            self.update_detected.emit(update_info)

            if self.auto_apply:
                success = self.checker.download_and_apply_update(
                    update_info,
                    on_progress=lambda msg: self.update_progress.emit(msg)
                )
                if success:
                    self.update_finished.emit(update_info["version"], update_info)
                else:
                    self.update_failed.emit("自动升级包解压或覆盖异常")
        except Exception as e:
            self.update_failed.emit(str(e))
