@echo off
chcp 65001 >nul
echo ========================================
echo    发票整理工具 - Web UI
echo ========================================
echo.
echo 正在启动 Streamlit 服务器...
echo.
echo 启动成功后会自动打开浏览器
echo 如未自动打开，请手动访问: http://localhost:8501
echo.
echo 按 Ctrl+C 可停止服务器
echo ========================================
echo.

cd /d "%~dp0"
streamlit run app.py

pause
