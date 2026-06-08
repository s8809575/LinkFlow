import sys
import os
import traceback

def main():
    log_file = os.path.join(os.path.dirname(sys.executable), 'launcher.log') if getattr(sys, 'frozen', False) else 'launcher.log'
    
    with open(log_file, 'w') as f:
        f.write(f"Python version: {sys.version}\n")
        f.write(f"sys.executable: {sys.executable}\n")
        f.write(f"sys.path: {sys.path}\n")
        f.write(f"frozen: {getattr(sys, 'frozen', False)}\n")
        f.write(f"_MEIPASS: {getattr(sys, '_MEIPASS', 'N/A')}\n")
        f.write("\n--- Starting main.py ---\n")
    
    try:
        # 导入并运行主程序
        import main
        main.main()
    except Exception as e:
        with open(log_file, 'a') as f:
            f.write(f"\n--- ERROR ---\n")
            f.write(f"Exception: {e}\n")
            f.write("Traceback:\n")
            f.write(traceback.format_exc())
        raise

if __name__ == "__main__":
    main()
