@echo off
cd /d "%~dp0"
echo [1] 开始诊断...
echo     当前目录: %CD%
echo.

echo [2] 检查管理员权限...
net session >nul 2>&1
if %errorlevel% equ 0 (
    echo     管理员: 是
) else (
    echo     管理员: 否
)
echo.

echo [3] 检查 Python...
where python
if %errorlevel% neq 0 (
    echo     [!] Python 未找到
) else (
    python --version
)
echo.

echo [4] 检查 main.py 是否存在...
if exist main.py (
    echo     main.py 存在
) else (
    echo     [!] main.py 不存在
    dir /b *.py
)
echo.

echo [5] 检查端口占用...
netstat -ano | findstr ":8766" | findstr "LISTENING" || echo     端口 8766 空闲
netstat -ano | findstr ":8767" | findstr "LISTENING" || echo     端口 8767 空闲
echo.

echo [6] 防火墙规则...
netsh advfirewall firewall show rule name="LinkFlow-WebSocket" >nul 2>&1 && echo     LinkFlow-WebSocket: 已配置 || echo     LinkFlow-WebSocket: 未配置
echo.

echo ========================================
echo  诊断完成，可截图此窗口给开发者
echo ========================================
pause
