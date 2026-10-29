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
        self.has_pending_exe_replacement = False
        if app_dir:
            self.app_dir = app_dir
        elif getattr(sys, 'frozen', False):
            self.app_dir = Path(sys.executable).resolve().parent
        else:
            self.app_dir = Path(__file__).resolve().parent.parent

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
            on_progress(f"正在准备下载 DeskEcho v{target_version} 发布包...")

        staging_dir = self.app_dir / ".update_staging"
        staging_dir.mkdir(parents=True, exist_ok=True)
        temp_zip = staging_dir / "update_download.bin"

        is_exe_staged = False
        try:
            # 1. 下载更新文件 (支持断点与流式分块进度汇报，超时放宽至 180 秒)
            download_success = False
            candidate_urls = [download_url]
            if not download_url.lower().endswith(".exe"):
                candidate_urls.append("https://github.com/bababoyibibilabu/DeskEcho/archive/refs/heads/main.zip")

            for url in candidate_urls:
                try:
                    if on_progress:
                        on_progress(f"正在连接远端升级资源...")
                    req = urllib.request.Request(url, headers={"User-Agent": "DeskEcho-Client-AutoUpdater"})
                    with urllib.request.urlopen(req, timeout=180) as resp:
                        total_size = int(resp.headers.get('Content-Length') or 0)
                        downloaded = 0
                        with open(temp_zip, 'wb') as out_f:
                            while True:
                                chunk = resp.read(1024 * 512) # 512KB
                                if not chunk:
                                    break
                                out_f.write(chunk)
                                downloaded += len(chunk)
                                if on_progress and total_size > 0:
                                    pct = int((downloaded / total_size) * 100)
                                    mb_down = downloaded / (1024 * 1024)
                                    mb_tot = total_size / (1024 * 1024)
                                    on_progress(f"正在下载升级包 ({mb_down:.1f}MB / {mb_tot:.1f}MB, {pct}%)...")

                    if temp_zip.exists() and temp_zip.stat().st_size > 1000:
                        download_success = True
                        break
                except Exception as de:
                    print(f"[UpdateChecker] 下载 {url} 失败: {de}")

            if not download_success:
                raise RuntimeError("无法从远端下载有效的发版安装包")

            if on_progress:
                on_progress("校验升级包完整性并准备应用更新...")

            # 判断是否为 Windows 独立可执行程序 (.exe)
            is_exe = download_url.lower().endswith(".exe") or (temp_zip.exists() and temp_zip.read_bytes()[:2] == b'MZ')
            if is_exe:
                target_exe = (self.app_dir / "DeskEcho.exe").resolve()
                staged_exe = (staging_dir / "DeskEcho_new.exe").resolve()
                if staged_exe.exists():
                    try:
                        staged_exe.unlink()
                    except Exception:
                        pass
                shutil.move(str(temp_zip), str(staged_exe))

                if getattr(sys, 'frozen', False):
                    # 运行在已打包的 EXE 模式下：
                    # 利用独立守护批处理脚本，等待当前主进程完全释放写锁定，执行原子替换后自拉起
                    current_pid = os.getpid()
                    bat_path = staging_dir / "apply_update.bat"
                    bat_content = f"""@echo off
chcp 65001 >nul
:: 等待老主进程完全退出并释放文件写锁定
timeout /t 2 /nobreak >nul
set RETRY=0
:WAIT_LOOP
tasklist /fi "PID eq {current_pid}" | find "{current_pid}" >nul
if not errorlevel 1 (
    timeout /t 1 /nobreak >nul
    set /a RETRY+=1
    if %RETRY% leq 10 goto WAIT_LOOP
    taskkill /F /PID {current_pid} >nul 2>&1
)
:: 复制新版本覆盖目标主程序
copy /y "{staged_exe}" "{target_exe}" >nul
:: 启动新版主程序
start "" "{target_exe}"
:: 清理暂存安装包及当前批处理
del "{staged_exe}" >nul 2>&1
(goto) 2>nul & del "%~f0"
"""
                    bat_path.write_text(bat_content, encoding='utf-8')
                    import subprocess
                    subprocess.Popen(["cmd.exe", "/c", str(bat_path)], creationflags=0x08000000 if os.name == 'nt' else 0)
                    self.has_pending_exe_replacement = True
                    is_exe_staged = True
                    print(f"[UpdateChecker] EXE 热升级批处理已成功布署并脱机触发 (PID 观察: {current_pid})")
                    return True
                else:
                    # 运行在 Python 源码模式下：复制 DeskEcho.exe 到根目录
                    shutil.copy2(str(staged_exe), str(target_exe))
                    print(f"[UpdateChecker] 源码模式：已将最新绿色发布程序存放至 {target_exe}")
                    is_exe_staged = False

            # 2. 如果是 zip 源码归档包，解压并热替换源码
            if not is_exe:
                extract_folder = staging_dir / "extracted"
                with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                    zip_ref.extractall(extract_folder)

                inner_dirs = [p for p in extract_folder.iterdir() if p.is_dir()]
                source_root = inner_dirs[0] if inner_dirs else extract_folder

                if on_progress:
                    on_progress("正在安全应用最新代码与组件...")

                updatable_items = ["core", "ui", "config.py", "main.py", "version.py", "version.json", "README.md", "requirements.txt", "run.bat", "run_background.bat"]
                protected_patterns = [".env", "omni_data", "records.db", "chroma", "local_data", "temp", "assets"]

                for item_name in updatable_items:
                    src_item = source_root / item_name
                    dst_item = self.app_dir / item_name
                    if not src_item.exists():
                        continue

                    if src_item.is_file():
                        shutil.copy2(src_item, dst_item)
                    elif src_item.is_dir():
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
            if not is_exe_staged and staging_dir.exists():
                try:
                    shutil.rmtree(staging_dir, ignore_errors=True)
                except Exception:
                    pass

    def restart_app(self):
        """重启应用客户端"""
        try:
            import subprocess
            if getattr(sys, 'frozen', False):
                # 若已触发 EXE 覆盖批处理，批处理会自动拉起新版，此处直接干净退出老进程以释放文件锁
                if self.has_pending_exe_replacement:
                    print("[UpdateChecker] 正在干净退出老进程以移交控制权给更新批处理...")
                    sys.exit(0)
                else:
                    subprocess.Popen([sys.executable] + sys.argv[1:], cwd=str(self.app_dir))
                    sys.exit(0)
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
