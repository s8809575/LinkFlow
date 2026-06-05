import subprocess
import sys
import os
import time

log_path = os.path.join(os.path.dirname(__file__), 'launcher_log.txt')

def log(message):
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(message + '\n')
    print(message)

log("="*50)
log(f"测试启动器开始, Python: {sys.version}")

# 测试运行主程序，捕获所有输出
log("\n[测试] 运行主程序并捕获输出")
try:
    exe_path = os.path.join(os.path.dirname(__file__), 'dist', 'LinkFlow.exe')
    log(f"EXE路径: {exe_path}")
    log(f"文件存在: {os.path.exists(exe_path)}")
    
    if os.path.exists(exe_path):
        # 使用 CREATE_NEW_CONSOLE 来显示控制台窗口，同时重定向输出
        process = subprocess.Popen(
            [exe_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        log("程序已启动")
        
        # 等待8秒让程序完成初始化和浏览器打开
        time.sleep(8)
        
        # 检查进程是否还在运行
        if process.poll() is None:
            log("进程仍在运行")
            # 获取输出
            try:
                stdout, _ = process.communicate(timeout=2)
                log(f"捕获的输出:\n{stdout}")
            except subprocess.TimeoutExpired:
                log("获取输出超时")
            # 终止进程
            process.terminate()
            process.wait()
            log("进程已终止")
        else:
            stdout, _ = process.communicate()
            log(f"进程已退出, 退出码: {process.returncode}")
            log(f"捕获的输出:\n{stdout}")
    else:
        log("EXE文件不存在")
        
except Exception as e:
    log(f"运行主程序失败: {e}")
    import traceback
    log(f"Traceback:\n{traceback.format_exc()}")

log("\n测试结束")