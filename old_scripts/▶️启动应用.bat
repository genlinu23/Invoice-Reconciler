@echo off
chcp 65001 >nul
title 发票整理工具

cd /d "%~dp0"

REM 检查EXE是否存在
if exist "dist\发票整理工具.exe" (
    echo [*] 启动应用...
    start "" "dist\发票整理工具.exe"
    exit
) else (
    echo.
    echo ========================================
    echo 应用程序未找到！
    echo ========================================
    echo.
    echo EXE文件不存在，正在自动打包...
    echo.
    python build_exe.py

    if exist "dist\发票整理工具.exe" (
        echo.
        echo 打包成功！正在启动...
        start "" "dist\发票整理工具.exe"
    ) else (
        echo.
        echo 打包失败，请手动运行：
        echo   python app_gui.py
    )

    pause
)
