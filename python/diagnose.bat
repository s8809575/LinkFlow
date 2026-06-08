@echo off
chcp 65001 >nul
echo ========================================
echo     LinkFlow 连接诊断工具
echo ========================================
echo.

:: 检查管理员权限
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] 注意：建议以管理员身份运行此脚本以获得完整诊断
    echo.
)

:: 1. 检查服务端口
echo [1/5] 检查服务端口状态...
echo.

netstat -ano | findstr ":8766" | findstr "LISTENING" >nul 2>&1
if %errorlevel% equ 0 (
    echo     OK 端口 8766 (HTTP) 正在监听
) else (
    echo     -- 端口 8766 未监听 - 服务可能未启动
)

netstat -ano | findstr ":8767" | findstr "LISTENING" >nul 2>&1
if %errorlevel% equ 0 (
    echo     OK 端口 8767 (WebSocket) 正在监听
) else (
    echo     -- 端口 8767 未监听 - 服务可能未启动
)

netstat -ano | findstr ":5000" | findstr "LISTENING" >nul 2>&1
if %errorlevel% equ 0 (
    echo     OK 端口 5000 (Server) 正在监听
) else (
    echo     -- 端口 5000 未监听
)

netstat -ano | findstr ":8089" | findstr "LISTENING" >nul 2>&1
if %errorlevel% equ 0 (
    echo     OK 端口 8089 (RPC) 正在监听
) else (
    echo     -- 端口 8089 未监听
)

:: 2. 检查网络配置
echo.
echo [2/5] 检查网络适配器配置...
echo.
ipconfig | findstr /C:"移动热点" /C:"WLAN 热点" /C:"无线局域网适配器" /C:"以太网" /C:"Wi-Fi"
echo.
echo 可用 IPv4 地址（供手机端连接）：
ipconfig | findstr /i "IPv4" | findstr /V "0\.0\.0\.0"

:: 3. 检查防火墙规则
echo.
echo [3/5] 检查防火墙设置...
echo.
set "FW_OK=1"
netsh advfirewall firewall show rule name="LinkFlow-WebSocket" >nul 2>&1
if %errorlevel% neq 0 set "FW_OK=0"
netsh advfirewall firewall show rule name="LinkFlow-Server" >nul 2>&1
if %errorlevel% neq 0 set "FW_OK=0"
netsh advfirewall firewall show rule name="LinkFlow-RPC" >nul 2>&1
if %errorlevel% neq 0 set "FW_OK=0"
if "%FW_OK%"=="1" (
    echo     OK 所有防火墙规则已配置 (8766,8767,5000,8089)
) else (
    echo     -- 部分防火墙规则缺失，请以管理员运行 start_linkflow.bat
)

:: 4. 检查依赖
echo.
echo [4/5] 检查Python依赖...
echo.
python -c "import websockets" 2>nul
if %errorlevel% equ 0 ( echo     OK websockets 已安装 ) else ( echo     -- websockets 未安装 )
python -c "import psutil" 2>nul
if %errorlevel% equ 0 ( echo     OK psutil 已安装 ) else ( echo     -- psutil 未安装 )
python -c "import win32api" 2>nul
if %errorlevel% equ 0 ( echo     OK pywin32 已安装 ) else ( echo     -- pywin32 未安装 )

:: 5. 总结
echo.
echo ========================================
echo     诊断总结
echo ========================================
echo.
echo 1. 如果端口未监听 - 运行 start_linkflow.bat
echo 2. 手机端输入上方IPv4地址连接
echo 3. 防火墙规则缺失时以管理员运行脚本
echo 4. 依赖缺失时运行: pip install -r requirements.txt
echo.
pause
