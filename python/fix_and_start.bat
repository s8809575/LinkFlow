@echo off
chcp 65001 >nul
echo ========================================
echo     LinkFlow 一键修复与启动
echo ========================================
echo.

:: 第1步：停止所有Python进程
echo [1/6] 停止所有Python进程...
taskkill /F /IM python.exe >nul 2>&1
timeout /t 2 /nobreak >nul
echo     OK

:: 第2步：验证端口已释放
echo.
echo [2/6] 验证端口状态...
netstat -ano | findstr ":8766" | findstr "LISTENING" >nul 2>&1
if %errorlevel% equ 0 (
    echo     -- 端口 8766 仍被占用，等待...
    timeout /t 5 /nobreak >nul
) else (
    echo     OK 端口 8766 已释放
)

:: 第3步：检查并安装依赖
echo.
echo [3/6] 检查依赖...
python -c "import websockets" 2>nul || ( echo     安装 websockets... & pip install websockets -q )
python -c "import psutil" 2>nul || ( echo     安装 psutil... & pip install psutil -q )
python -c "import win32api" 2>nul || ( echo     安装 pywin32... & pip install pywin32 -q )
echo     OK 依赖检查完成

:: 第4步：添加防火墙规则
echo.
echo [4/6] 配置防火墙规则...
netsh advfirewall firewall add rule name="LinkFlow-WebSocket" dir=in action=allow protocol=TCP localport=8766,8767 >nul 2>&1
netsh advfirewall firewall add rule name="LinkFlow-Server" dir=in action=allow protocol=TCP localport=5000 >nul 2>&1
netsh advfirewall firewall add rule name="LinkFlow-RPC" dir=in action=allow protocol=TCP localport=8089 >nul 2>&1
echo     OK 防火墙规则已添加

:: 第5步：显示网络信息
echo.
echo [5/6] 网络配置信息...
echo.
echo     手机端请填入以下任一IPv4地址连接：
ipconfig | findstr /i "IPv4" | findstr /V "0\.0\.0\.0"

:: 第6步：启动服务
echo.
echo [6/6] 启动LinkFlow服务...
echo.
cd /d "%~dp0"
set PYTHONPATH=%CD%
start "LinkFlow" cmd /k "python main.py"
timeout /t 3 /nobreak >nul

:: 验证服务
netstat -ano | findstr ":8766" | findstr "LISTENING" >nul 2>&1
if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo     OK 服务启动成功！
    echo ========================================
    echo.
    echo     在手机浏览器中打开 http://上面的IP:8766
    echo     在页面中输入该IP地址，点击"连接"
    echo.
) else (
    echo.
    echo ========================================
    echo     -- 服务启动可能有问题
    echo ========================================
    echo.
    echo     请检查上方输出中的错误信息
)
pause
