@echo off
chcp 65001 >nul
title 生成Word报告

cd /d "%~dp0"

echo ========================================
echo 生成Word报告
echo ========================================
echo.

python tools/generate_word.py

pause
