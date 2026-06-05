import subprocess
import sys
import os
import time

log_path = os.path.join(os.path.dirname(__file__), 'direct_test_log.txt')

def log(message):
    print(message)
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(message + '\n')

log("="*50)
log(f"测试开始, Python: {sys.version}")

# 运行目录版本的程序
exe_path = os.path.join(os.path.dirname(__file__), 'dist', 'LinkFlow', 'LinkFlow.exe')
log(f"EXE路径: {exe_path}")
log(f"文件存在: {os.path.exists(exe_path)}")

if os.path.exists(exe_path):
    log("\n启动程序...")
    
    # 直接启动程序，使用新控制台窗口
    process = subprocess.Popen(
        [exe_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    
    log("程序已启动")
    
    # 读取输出
    start_time = time.time()
    while time.time() - start_time < 10:
        if process.poll() is not None:
            log(f"程序已退出，退出码: {process.returncode}")
            break
        
        try:
            line = process.stdout.readline()
            if line:
                log(f"程序输出: {line.strip()}")
        except:
            pass
        
        time.sleep(0.5)
    
    # 终止进程
    if process.poll() is None:
        log("终止程序...")
        process.terminate()
        process.wait()

log("\n测试结束")