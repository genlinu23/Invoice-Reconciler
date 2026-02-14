@echo off
chcp 65001 >nul
echo ========================================
echo    发票整理工具 - 启动
echo ========================================
echo.

cd /d "%~dp0"

python app_gui.py

pause
