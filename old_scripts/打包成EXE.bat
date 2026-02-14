@echo off
chcp 65001 >nul
echo ========================================
echo    发票整理工具 - 打包成 EXE
echo ========================================
echo.
echo 正在检查依赖...
echo.

cd /d "%~dp0"

:: 检查是否安装了 pyinstaller
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo PyInstaller 未安装，正在安装...
    pip install pyinstaller
)

echo.
echo 开始打包...
echo.

python build_exe.py

echo.
echo ========================================
echo 打包完成！
echo ========================================
echo.
pause
