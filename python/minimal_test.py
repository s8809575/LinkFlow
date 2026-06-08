import sys
import os

log_path = os.path.join(os.path.dirname(__file__), 'minimal_test_log.txt')

def log(message):
    print(message)
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(message + '\n')

log("="*50)
log(f"测试开始, Python: {sys.version}")
log(f"sys.executable: {sys.executable}")
log(f"frozen: {getattr(sys, 'frozen', False)}")

try:
    log("\n[测试1] 导入基础模块")
    import time
    import threading
    import subprocess
    import webbrowser
    log("基础模块导入成功")
    
    log("\n[测试2] 检查路径")
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
        log(f"_MEIPASS: {base_path}")
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
        log(f"base_path: {base_path}")
    
    log("\n[测试3] 测试浏览器打开")
    try:
        subprocess.run(['powershell.exe', '-Command', 'Start-Process "http://localhost:8766/desktop"'], check=True)
        log("浏览器打开成功")
    except Exception as e:
        log(f"浏览器打开失败: {e}")
    
    log("\n测试完成")
    
except Exception as e:
    log(f"测试失败: {e}")
    import traceback
    log(f"Traceback:\n{traceback.format_exc()}")