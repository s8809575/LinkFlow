import socket
import time
import sys

def test_tcp_connection(ip, port=5000, timeout=5):
    """测试TCP连接"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except Exception as e:
        print(f"TCP连接测试异常: {e}")
        return False

def test_websocket_connection(ip, port=8767, timeout=5):
    """测试WebSocket连接"""
    try:
        import websockets
        import asyncio
        
        async def test_ws():
            try:
                async with websockets.connect(f'ws://{ip}:{port}', timeout=timeout) as websocket:
                    await websocket.send('{"type": "heartbeat"}')
                    response = await asyncio.wait_for(websocket.recv(), timeout=timeout)
                    return True, response
            except Exception as e:
                return False, str(e)
        
        success, response = asyncio.run(test_ws())
        return success, response
    except ImportError:
        print("未安装websockets库")
        return False, "缺少依赖"
    except Exception as e:
        return False, str(e)

def get_local_ips():
    """获取本地IP地址"""
    try:
        hostname = socket.gethostname()
        ip_list = socket.getaddrinfo(hostname, None, socket.AF_INET)
        ips = list(set([info[4][0] for info in ip_list]))
        return ips
    except Exception as e:
        print(f"获取IP失败: {e}")
        return []

def check_server_status():
    """检查服务器状态"""
    print("="*60)
    print("LinkFlow 连接诊断工具")
    print("="*60)
    
    # 1. 检查本地IP
    print("\n[1/6] 检查本地IP地址...")
    ips = get_local_ips()
    if ips:
        print("   本地IP地址:")
        for ip in ips:
            print(f"     - {ip}")
    else:
        print("   ✗ 无法获取本地IP")
    
    # 2. 检查服务器端口
    print("\n[2/6] 检查服务器端口...")
    ports = {
        5000: "TCP Server (手机TCP连接)",
        8766: "HTTP Server (静态文件)",
        8767: "WebSocket Server",
        8089: "RPC Server"
    }
    
    for port, desc in ports.items():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        
        if result == 0:
            print(f"   ✓ {port}端口 - {desc}")
        else:
            print(f"   ✗ {port}端口 - {desc} (未监听)")
    
    # 3. 测试本地WebSocket连接
    print("\n[3/6] 测试本地WebSocket连接...")
    success, response = test_websocket_connection('127.0.0.1')
    if success:
        print(f"   ✓ WebSocket连接成功")
        print(f"     响应: {response}")
    else:
        print(f"   ✗ WebSocket连接失败: {response}")
    
    # 4. 测试网络信息接口
    print("\n[4/6] 测试网络信息接口...")
    try:
        import websockets
        import asyncio
        import json
        
        async def test_network_info():
            async with websockets.connect('ws://127.0.0.1:8767') as websocket:
                await websocket.send(json.dumps({"req_id": "test", "type": "get_network_info"}))
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                return json.loads(response)
        
        info = asyncio.run(test_network_info())
        if info.get('hotspot_ip'):
            print(f"   ✓ 获取网络信息成功")
            print(f"     热点IP: {info['hotspot_ip']}")
            print(f"     主机名: {info['hostname']}")
            print(f"     所有IP: {', '.join(info['ips'])}")
        else:
            print("   ✗ 获取网络信息失败")
    except Exception as e:
        print(f"   ✗ 测试失败: {e}")
    
    # 5. 检查防火墙规则
    print("\n[5/6] 检查防火墙规则...")
    try:
        import subprocess
        result = subprocess.run(
            ['netsh', 'advfirewall', 'firewall', 'show', 'rule', 'name=LinkFlow-WebSocket'],
            capture_output=True, text=True
        )
        if "LinkFlow-WebSocket" in result.stdout:
            print("   ✓ LinkFlow-WebSocket 防火墙规则已配置")
        else:
            print("   ⚠️ 未找到LinkFlow-WebSocket防火墙规则")
    except Exception as e:
        print(f"   无法检查防火墙: {e}")
    
    # 6. 提供连接建议
    print("\n[6/6] 连接建议...")
    print("   ┌─────────────────────────────────────────────────────────┐")
    print("   │ 手机端连接步骤:                                        │")
    print("   │ 1. 确保手机和电脑连接到同一网络（推荐手机热点）          │")
    print("   │ 2. 在手机端输入电脑IP地址（如192.168.43.x）            │")
    print("   │ 3. 点击连接按钮                                        │")
    print("   │                                                        │")
    print("   │ 常见问题排查:                                          │")
    print("   │ • 确保电脑IP地址正确                                    │")
    print("   │ • 确保端口8766, 8767, 5000未被占用                      │")
    print("   │ • 检查防火墙是否阻止连接                                │")
    print("   │ • 尝试重启LinkFlow服务                                  │")
    print("   └─────────────────────────────────────────────────────────┘")
    
    print("\n" + "="*60)
    print("诊断完成！")
    print("="*60)

if __name__ == "__main__":
    check_server_status()
