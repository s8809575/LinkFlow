import sys
import os

log_path = os.path.join(os.path.dirname(__file__), 'import_test_log.txt')

def log(message):
    print(message)
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(message + '\n')

log("="*50)
log(f"测试开始, Python: {sys.version}")

try:
    log("\n[测试1] 设置路径")
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    log(f"base_path: {base_path}")
    sys.path.insert(0, os.path.join(base_path, 'linkflow'))
    log("路径设置完成")
    
    log("\n[测试2] 导入基础模块")
    import time
    import threading
    import asyncio
    import base64
    log("基础模块导入成功")
    
    log("\n[测试3] 导入 core.server")
    try:
        from core.server import LinkFlowServer
        log("LinkFlowServer 导入成功")
    except Exception as e:
        log(f"LinkFlowServer 导入失败: {e}")
        import traceback
        log(f"Traceback:\n{traceback.format_exc()}")
        
    log("\n[测试4] 导入 core.protocol")
    try:
        from core.protocol import LinkFlowProtocol
        log("LinkFlowProtocol 导入成功")
    except Exception as e:
        log(f"LinkFlowProtocol 导入失败: {e}")
        import traceback
        log(f"Traceback:\n{traceback.format_exc()}")
        
    log("\n[测试5] 导入 core.utils")
    try:
        from core.utils import WebBridge
        log("WebBridge 导入成功")
    except Exception as e:
        log(f"WebBridge 导入失败: {e}")
        import traceback
        log(f"Traceback:\n{traceback.format_exc()}")
        
    log("\n[测试6] 导入 core.clipboard_service")
    try:
        from core.clipboard_service import ClipboardService
        log("ClipboardService 导入成功")
    except Exception as e:
        log(f"ClipboardService 导入失败: {e}")
        import traceback
        log(f"Traceback:\n{traceback.format_exc()}")
        
    log("\n[测试7] 导入 core.rpc_server")
    try:
        from core.rpc_server import LinkFlowRpcServer
        log("LinkFlowRpcServer 导入成功")
    except Exception as e:
        log(f"LinkFlowRpcServer 导入失败: {e}")
        import traceback
        log(f"Traceback:\n{traceback.format_exc()}")
        
    log("\n[测试8] 导入 core.mdns_service")
    try:
        from core.mdns_service import MdnsService
        log("MdnsService 导入成功")
    except Exception as e:
        log(f"MdnsService 导入失败: {e}")
        import traceback
        log(f"Traceback:\n{traceback.format_exc()}")
        
    log("\n[测试9] 导入 core.monitor_service")
    try:
        from core.monitor_service import MonitorService
        log("MonitorService 导入成功")
    except Exception as e:
        log(f"MonitorService 导入失败: {e}")
        import traceback
        log(f"Traceback:\n{traceback.format_exc()}")
        
    log("\n测试完成")
    
except Exception as e:
    log(f"测试失败: {e}")
    import traceback
    log(f"Traceback:\n{traceback.format_exc()}")