@echo off
chcp 65001 >nul
echo [DeskEcho] 正在启动敏捷自进化巡检守护进程...
cd /d "%~dp0"
uv run python scripts/watch_iteration_queue.py
pause
