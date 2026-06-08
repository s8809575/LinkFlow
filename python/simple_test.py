import sys
import os

print("=== Simple Test ===")
print(f"Python version: {sys.version}")
print(f"sys.executable: {sys.executable}")
print(f"frozen: {getattr(sys, 'frozen', False)}")
print(f"_MEIPASS: {getattr(sys, '_MEIPASS', 'N/A')}")
print(f"Current dir: {os.getcwd()}")

# 尝试打开浏览器
import subprocess
try:
    print("\nTrying to open browser...")
    subprocess.run(['start', 'http://localhost:8766/desktop'], shell=True)
    print("Browser opened successfully")
except Exception as e:
    print(f"Failed to open browser: {e}")

# 保持运行
import time
print("\nRunning... Press Ctrl+C to exit")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nExiting...")
