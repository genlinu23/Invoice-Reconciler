@echo off
chcp 65001 >nul
title 清空输出文件夹

cd /d "%~dp0"

echo ========================================
echo 清空输出文件夹
echo ========================================
echo.
echo 警告：这将删除 "发票\output" 文件夹中的所有文件！
echo.
pause

python tools/clear_output.py

pause
