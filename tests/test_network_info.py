import asyncio
import websockets

async def test_network_info():
    """测试网络信息接口"""
    try:
        async with websockets.connect('ws://localhost:8766') as websocket:
            print("连接成功")
            
            # 发送获取网络信息请求
            request = {
                "req_id": "test123",
                "type": "get_network_info"
            }
            await websocket.send(str(request).replace("'", '"'))
            print("已发送请求")
            
            # 等待响应
            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            print(f"收到响应: {response}")
            
            return True
    except asyncio.TimeoutError:
        print("超时错误")
        return False
    except Exception as e:
        print(f"连接失败: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_network_info())
