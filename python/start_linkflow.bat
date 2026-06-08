@echo off
cd /d "%~dp0"

:: 检查管理员权限
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ================================================
    echo [!] 需要管理员权限才能运行此脚本
    echo ================================================
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    timeout /t 2 >nul
    exit
)

:: 1. 添加防火墙规则
echo [1/3] 配置防火墙规则...
netsh advfirewall firewall add rule name="LinkFlow-WebSocket" dir=in action=allow protocol=TCP localport=8766,8767 >nul 2>&1
netsh advfirewall firewall add rule name="LinkFlow-Server" dir=in action=allow protocol=TCP localport=5000 >nul 2>&1
netsh advfirewall firewall add rule name="LinkFlow-RPC" dir=in action=allow protocol=TCP localport=8089 >nul 2>&1
echo     OK

:: 2. 检测IP
echo [2/3] 检测IP...
ipconfig | findstr "IPv4"
echo.

:: 3. 启动服务
echo [3/3] 启动 LinkFlow 服务...
set PYTHONPATH=%CD%
start "LinkFlow" cmd /k "python main.py"
timeout /t 2 >nul
echo     OK

echo.
echo 服务已启动，请在手机浏览器访问 http://电脑IP:8766
echo.
echo 手机端IP输入框填入上面的IPv4地址，点击连接
echo.
pause
