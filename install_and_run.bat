@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ==================================================
echo   DeskEcho 桌面回响 · 笔记本实机环境初始化
echo ==================================================

if exist ".venv\Scripts\python.exe" goto RUN

echo [1/3] 正在检测 Python 环境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 本机尚未安装 Python，请先从 python.org 安装 Python 3.10 或 3.11 并勾选 Add to PATH。
    pause
    exit /b 1
)

echo [2/3] 正在创建 Python 虚拟环境 (.venv)...
python -m venv .venv
if %errorlevel% neq 0 (
    echo [错误] 创建虚拟环境失败。
    pause
    exit /b 1
)

echo [3/3] 正在极速安装核心运行依赖 (PyQt6, PyAudio, ChromaDB, Edge-TTS等)...
.venv\Scripts\python.exe -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
.venv\Scripts\python.exe -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if %errorlevel% neq 0 (
    echo [提示] 正在尝试官方源重试安装...
    .venv\Scripts\python.exe -m pip install -r requirements.txt
)

:RUN
echo ==================================================
echo   环境就绪，正在启动 DeskEcho 控制台...
echo   按住【右 Alt】开启对讲，松开检索 (免按 Fn 快捷键)！
echo ==================================================
.venv\Scripts\python.exe main.py
if errorlevel 1 pause
