import asyncio
import json
import threading
import os
import sys
from urllib.parse import urlparse

# 处理 PyInstaller 打包后的路径问题
if getattr(sys, 'frozen', False):
    # 打包后的运行环境
    BASE_PATH = sys._MEIPASS
else:
    # 开发环境
    BASE_PATH = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class WebBridge:
    def __init__(self, port=8766):
        self.port = port
        self.clients = set()
        self.loop = None

    async def handle_http(self, reader, writer):
        """处理HTTP请求，提供静态文件服务"""
        try:
            # 读取HTTP请求
            data = await reader.read(4096)
            if not data:
                writer.close()
                await writer.wait_closed()
                return
            
            request = data.decode('utf-8', errors='replace')
            lines = request.split('\r\n')
            if not lines:
                writer.close()
                await writer.wait_closed()
                return
            
            # 解析请求行
            request_line = lines[0]
            # 过滤掉请求行中的非ASCII字符（浏览器探测请求可能包含异常字节）
            request_line = ''.join(c for c in request_line if c.isascii())
            parts = request_line.split()
            if len(parts) < 2:
                writer.close()
                await writer.wait_closed()
                return
            
            method = parts[0]
            path = parts[1]
            
            # 获取web目录路径
            web_dir = os.path.join(BASE_PATH, 'web')
            
            # 处理路径
            # 移除末尾斜杠
            path = path.rstrip('/')
            
            if path == '/' or path == '' or path == '/index.html':
                file_path = os.path.join(web_dir, 'desktop', 'index.html')
            elif path == '/desktop':
                file_path = os.path.join(web_dir, 'desktop', 'index.html')
            elif path.startswith('/desktop/'):
                file_path = os.path.join(web_dir, path[1:])
            elif path == '/mobile':
                file_path = os.path.join(web_dir, 'mobile', 'index.html')
            elif path.startswith('/mobile/'):
                file_path = os.path.join(web_dir, path[1:])
            elif path.startswith('/static/'):
                file_path = os.path.join(web_dir, path[1:])
            else:
                # 默认返回电脑端页面
                file_path = os.path.join(web_dir, 'desktop', 'index.html')
            
            # 安全检查：防止路径遍历
            if not file_path.startswith(web_dir):
                response = "HTTP/1.1 403 Forbidden\r\nContent-Length: 13\r\n\r\nForbidden"
                writer.write(response.encode())
                await writer.drain()
                writer.close()
                await writer.wait_closed()
                return
            
            # 读取文件
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()
                
                # 确定Content-Type
                if file_path.endswith('.html'):
                    content_type = 'text/html; charset=utf-8'
                elif file_path.endswith('.css'):
                    content_type = 'text/css; charset=utf-8'
                elif file_path.endswith('.js'):
                    content_type = 'application/javascript; charset=utf-8'
                elif file_path.endswith('.png'):
                    content_type = 'image/png'
                elif file_path.endswith('.jpg') or file_path.endswith('.jpeg'):
                    content_type = 'image/jpeg'
                elif file_path.endswith('.svg'):
                    content_type = 'image/svg+xml'
                else:
                    content_type = 'application/octet-stream'
                
                response = f"HTTP/1.1 200 OK\r\nContent-Type: {content_type}\r\nContent-Length: {len(content)}\r\n\r\n".encode() + content
            except FileNotFoundError:
                response = "HTTP/1.1 404 Not Found\r\nContent-Length: 9\r\n\r\nNot Found".encode()
            except Exception as e:
                response = f"HTTP/1.1 500 Internal Server Error\r\nContent-Length: {len(str(e))}\r\n\r\n{str(e)}".encode()
            
            writer.write(response)
            await writer.drain()
        except Exception as e:
            print(f"[!] HTTP处理异常: {e}")
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except:
                pass

    async def register(self, websocket):
        """当网页连接时调用"""
        self.clients.add(websocket)
        client_count = len(self.clients)
        print(f"[*] WebBridge: 新客户端连接，当前客户端数: {client_count}")
        try:
            # 必须添加这个循环来监听网页消息
            async for message in websocket:
                data = json.loads(message)
                print(f"[*] WebBridge: 收到消息: {data.get('type', 'unknown')}")
                if hasattr(self, 'on_message_hook') and self.on_message_hook:
                    await self.on_message_hook(data)
        except Exception as e:
            print(f"[!] Bridge 异常: {e}")
        finally:
            self.clients.discard(websocket)
            client_count = len(self.clients)
            print(f"[*] WebBridge: 客户端断开，当前客户端数: {client_count}")

            self.broadcast({
                "type": "device_disconnected"
            })

    async def _send_to_all(self, data):
        """内部异步发送函数"""
        if self.clients:
            message = json.dumps(data)
            # 使用 wait 批量发送，忽略个别客户端断开的错误
            await asyncio.gather(*[client.send(message) for client in self.clients], return_exceptions=True)

    def broadcast(self, data):
        """供外部 Python 线程调用的非异步接口"""
        if self.loop and self.loop.is_running():
            client_count = len(self.clients) if self.clients else 0
            if client_count == 0:
                print(f"[!] WebBridge.broadcast: 没有连接的客户端")
                return
            print(f"[*] WebBridge.broadcast: 向 {client_count} 个客户端发送消息: {data.get('type', 'unknown')}")
            # 将发送任务安全地推送到异步线程中执行
            self.loop.call_soon_threadsafe(
                lambda d=data: self.loop.create_task(self._send_to_all(d))
            )

    async def _start(self):
        """异步环境的主入口"""
        try:
            import websockets
        except ImportError as e:
            raise RuntimeError("缺少依赖: websockets，请先安装后再启动 WebBridge") from e

        self.loop = asyncio.get_running_loop()
        
        # 启动HTTP服务器
        http_server = await asyncio.start_server(self.handle_http, "0.0.0.0", self.port)
        print(f"[*] HTTP 静态文件服务已就绪: http://0.0.0.0:{self.port}")
        
        # 启动WebSocket服务器（使用不同端口）
        websocket_port = self.port + 1
        async with websockets.serve(self.register, "0.0.0.0", websocket_port):
            print(f"[*] WebSocket 服务已就绪: ws://0.0.0.0:{websocket_port}")
            await asyncio.Future()  # 保持运行

    def start_bridge(self):
        """在独立线程中启动异步循环"""
        def run_async_logic():
            try:
                asyncio.run(self._start())
            except Exception as e:
                print(f"[!] 前端网桥运行异常: {e}")

        t = threading.Thread(target=run_async_logic, daemon=True)
        t.start()
