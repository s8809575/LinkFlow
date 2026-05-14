import platform
import os
import ctypes
from core.protocol import LinkFlowProtocol

class MonitorService:
    """
    模块三 & 模块四：系统监控与应急控制服务
    负责采集硬件数据并执行系统级指令
    """

    @staticmethod
    def get_system_stats():
        """
        获取当前硬件状态仪表盘数据
        对应设计全案中的性能监控功能
        """
        try:
            import psutil
        except ImportError:
            psutil = None

        stats = {
            "cpu_percent": psutil.cpu_percent(interval=None) if psutil else 0,
            "memory_percent": psutil.virtual_memory().percent if psutil else 0,
            "battery_percent": 0,
            "os_info": f"{platform.system()} {platform.release()}"
        }
        
        # 获取电池信息（如果是笔记本）
        if psutil:
            try:
                battery = psutil.sensors_battery()
                if battery:
                    stats["battery_percent"] = battery.percent
            except Exception:
                pass
            
        return stats

    @staticmethod
    def execute_control_command(command):
        """
        执行远程应急操作
        对应设计全案中的一键应急操作功能
        """
        try:
            if command == "mute":
                # Windows 静音指令 (发送虚拟按键码 0xAD)
                ctypes.windll.user32.SendMessageW(0xFFFF, 0x0319, 0, 0x80000)
            elif command == "sleep":
                # 系统进入睡眠状态
                os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            elif command == "screen_off":
                # 息屏 (发送系统消息 0x0112, 参数 0xF170)
                ctypes.windll.user32.SendMessageW(0xFFFF, 0x0112, 0xF170, 2)
            elif command == "reboot":
                os.system("shutdown /r /t 1")
            return True
        except Exception as e:
            print(f"[!] 指令执行失败: {e}")
            return False

    @staticmethod
    def get_screen_snapshot():
        """
        获取屏幕快照预览逻辑（占位）
        后续可引入 pyautogui 实现实时截屏预览
        """
        pass
