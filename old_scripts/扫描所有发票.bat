@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================================
echo 发票扫描工具 - 正在扫描所有PDF文件
echo ============================================================
echo.

REM 使用conda的Python
set PYTHON_EXE=C:\Users\17193\miniconda3\python.exe

if not exist "%PYTHON_EXE%" (
    echo 错误: 找不到 conda Python
    echo 尝试使用系统Python...
    set PYTHON_EXE=python
)

echo 使用Python: %PYTHON_EXE%
echo.

REM 运行GUI工具
echo 正在启动GUI工具，请在界面中点击"处理发票"按钮...
echo.
%PYTHON_EXE% app_gui.py

pause
