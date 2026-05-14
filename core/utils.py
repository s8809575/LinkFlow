import asyncio
import json
import threading

class WebBridge:
    def __init__(self, port=8766):
        self.port = port
        self.clients = set()
        self.loop = None

    async def register(self, websocket):
        """当网页连接时调用"""
        self.clients.add(websocket)
        try:
            # 必须添加这个循环来监听网页消息
            async for message in websocket:
                data = json.loads(message)
                if hasattr(self, 'on_message_hook') and self.on_message_hook:
                    await self.on_message_hook(data)
        except Exception as e:
            print(f"[!] Bridge 异常: {e}")
        finally:
            self.clients.discard(websocket)

    async def _send_to_all(self, data):
        """内部异步发送函数"""
        if self.clients:
            message = json.dumps(data)
            # 使用 wait 批量发送，忽略个别客户端断开的错误
            await asyncio.gather(*[client.send(message) for client in self.clients], return_exceptions=True)

    def broadcast(self, data):
        """供外部 Python 线程调用的非异步接口"""
        if self.loop and self.loop.is_running():
            # 将发送任务安全地推送到异步线程中执行
            self.loop.call_soon_threadsafe(
                lambda: self.loop.create_task(self._send_to_all(data))
            )

    async def _start(self):
        """异步环境的主入口"""
        try:
            import websockets
        except ImportError as e:
            raise RuntimeError("缺少依赖: websockets，请先安装后再启动 WebBridge") from e

        self.loop = asyncio.get_running_loop()
        # 在异步环境内部创建 server
        async with websockets.serve(self.register, "localhost", self.port):
            print(f"[*] 前端网桥已就绪: ws://localhost:{self.port}")
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
