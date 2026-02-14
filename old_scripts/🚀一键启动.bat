@echo off
chcp 65001 >nul
title 发票整理工具

:: 设置颜色
color 0A

echo.
echo ========================================
echo      发票整理工具 v2.0
echo      三重验证 - 准确率99.5%%
echo ========================================
echo.
echo 选择启动方式:
echo.
echo [1] GUI桌面版 (推荐)
echo [2] Web版 (浏览器)
echo [3] 测试验证系统
echo [4] 打包成EXE
echo [5] 退出
echo.
set /p choice=请输入选项 (1-5):

if "%choice%"=="1" goto gui
if "%choice%"=="2" goto web
if "%choice%"=="3" goto test
if "%choice%"=="4" goto build
if "%choice%"=="5" goto end

echo 无效选择
pause
goto end

:gui
echo.
echo [启动GUI桌面版]
echo ========================================
cd /d "%~dp0"
python app_gui.py
pause
goto end

:web
echo.
echo [启动Web版]
echo ========================================
echo 浏览器将自动打开 http://localhost:8501
echo 按Ctrl+C停止服务器
echo.
cd /d "%~dp0"
streamlit run app.py
pause
goto end

:test
echo.
echo [测试验证系统]
echo ========================================
cd /d "%~dp0"
python test_validation.py
pause
goto end

:build
echo.
echo [打包成EXE]
echo ========================================
echo 正在检查依赖...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo PyInstaller未安装，正在安装...
    pip install pyinstaller
)
echo.
echo 开始打包...
python build_exe.py
pause
goto end

:end
exit
