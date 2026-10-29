# 笔记本端 DeskEcho 安全重启脚本
Write-Host ">>> 正在终止笔记本上现有的 DeskEcho / Python 进程..." -ForegroundColor Yellow
ssh Administrator@192.168.1.166 "taskkill /f /im python.exe >nul 2>&1"
Start-Sleep -Seconds 1

Write-Host ">>> 正在拉起全新 DeskEcho 客户端会话..." -ForegroundColor Cyan
ssh Administrator@192.168.1.166 "schtasks /run /tn DeskEchoLaunch"
Start-Sleep -Seconds 2

Write-Host ">>> 校验运行进程状态..." -ForegroundColor Green
ssh Administrator@192.168.1.166 "tasklist | findstr python"
