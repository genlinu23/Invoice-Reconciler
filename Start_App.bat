@echo off
chcp 65001 >nul
title 发票整理工具 - 启动

cd /d "%~dp0"

echo ========================================
echo 发票整理工具
echo ========================================
echo.

python app.py

pause
