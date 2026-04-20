@echo off
chcp 65001 >nul
echo === 炸金花游戏服务器 ===
echo.
cd /d "%~dp0"
python -c "from backend.app import run_server; run_server()"
pause
