import platform
import os
import ctypes

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
            print(f"[*] 执行控制命令: {command}")
            
            if command == "mute":
                # Windows 音量控制 (使用 SendInput 切换静音)
                try:
                    VK_VOLUME_MUTE = 0xAD
                    ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, 0, 0)
                    ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, 2, 0)
                    print("[*] 静音命令已执行")
                except Exception as e:
                    print(f"[!] 静音执行失败: {e}")
            elif command == "sleep":
                # 系统进入睡眠状态
                os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            elif command == "screen_off":
                try:
                    WM_SYSCOMMAND = 0x0112
                    SC_MONITORPOWER = 0xF170
                    MONITOR_OFF = 2
                    SMTO_ABORTIFHUNG = 0x0002
                    result = ctypes.c_ulong()

                    user32 = ctypes.windll.user32

                    hwnd = user32.GetForegroundWindow()

                    if not hwnd:
                        hwnd = 0xFFFF

                    user32.SendMessageTimeoutW(
                        hwnd,
                        WM_SYSCOMMAND,
                        SC_MONITORPOWER,
                        MONITOR_OFF,
                        SMTO_ABORTIFHUNG,
                        1000,
                        ctypes.byref(result),
                    )
                    
                    print("[*] 息屏命令已发出")
                except Exception as e:
                    print(f"[!] 息屏执行失败: {e}")
                    return False
            elif command == "keep_awake":
                # 保持系统唤醒，避免服务断开；不强制显示器常亮
                try:
                    ES_CONTINUOUS = 0x80000000
                    ES_SYSTEM_REQUIRED = 0x00000001
                    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
                    print("[*] 已启用防息屏模式")
                except Exception as e:
                    print(f"[!] 防息屏设置失败: {e}")
            elif command == "allow_sleep":
                # 允许系统自动息屏
                try:
                    ES_CONTINUOUS = 0x80000000
                    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
                    print("[*] 已恢复系统息屏")
                except Exception as e:
                    print(f"[!] 恢复息屏失败: {e}")
            elif command == "reboot" or command == "restart":
                os.system("shutdown /r /t 1")
            return True
        except Exception as e:
            print(f"[!] 指令执行失败: {e}")
            return False

    @staticmethod
    def get_screen_snapshot():
        """
        获取屏幕快照预览
        使用 Windows API 捕获屏幕并返回 Base64 编码的 PNG 图片
        """
        try:
            import win32api
            import win32con
            import win32gui
            import win32ui
            import io
            import base64
            
            # 获取屏幕尺寸
            hdesktop = win32gui.GetDesktopWindow()
            width = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
            height = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)
            left = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
            top = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)
            
            # 创建设备上下文
            desktop_dc = win32gui.GetWindowDC(hdesktop)
            img_dc = win32ui.CreateDCFromHandle(desktop_dc)
            mem_dc = img_dc.CreateCompatibleDC()
            
            # 创建位图
            screenshot = win32ui.CreateBitmap()
            screenshot.CreateCompatibleBitmap(img_dc, width, height)
            mem_dc.SelectObject(screenshot)
            
            # 拷贝屏幕内容
            mem_dc.BitBlt((0, 0), (width, height), img_dc, (left, top), win32con.SRCCOPY)
            
            # 转换为 PIL Image (使用更简单的方式避免依赖)
            try:
                from PIL import Image
                bmpinfo = screenshot.GetInfo()
                bmpstr = screenshot.GetBitmapBits(True)
                img = Image.frombuffer(
                    'RGB',
                    (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                    bmpstr, 'raw', 'BGRX', 0, 1
                )
                buffer = io.BytesIO()
                img.save(buffer, format='PNG')
                image_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            except ImportError:
                # 如果没有PIL，使用BMP格式（更大但不需要额外库）
                print("[!] PIL未安装，使用BMP格式")
                bmpinfo = screenshot.GetInfo()
                bmpstr = screenshot.GetBitmapBits(True)
                # 创建简单的PNG替代方案
                # 直接返回BMP的base64
                image_b64 = base64.b64encode(bmpstr).decode('utf-8')
                return {
                    "image_b64": image_b64,
                    "width": width,
                    "height": height,
                    "format": "bmp",
                    "error": "PIL not installed, using BMP format"
                }
            
            # 清理资源
            mem_dc.DeleteDC()
            win32gui.DeleteObject(screenshot.GetHandle())
            win32gui.ReleaseDC(hdesktop, desktop_dc)
            
            return {
                "image_b64": image_b64,
                "width": width,
                "height": height,
                "format": "png"
            }
        except Exception as e:
            print(f"[!] 截图失败: {e}")
            return {"error": str(e), "error_type": "SCREENSHOT_FAILED"}
