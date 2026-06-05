from playwright.sync_api import sync_playwright
import sys
import time

def test_desktop_full():
    """完整测试电脑端界面"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # 使用非无头模式便于观察
        page = browser.new_page()
        
        console_logs = []
        page.on('console', lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        
        try:
            # 打开电脑端页面
            page.goto('http://localhost:8766/desktop/')
            page.wait_for_load_state('domcontentloaded')
            page.wait_for_timeout(3000)  # 等待3秒让页面初始化
            
            print("="*60)
            print("电脑端界面完整测试")
            print("="*60)
            
            # 1. 检查页面加载
            print("\n1. 检查页面加载...")
            header = page.locator('.header-bar')
            assert header.is_visible(), "页面未正确加载"
            print("   ✓ 页面加载成功")
            
            # 2. 检查WebSocket连接状态
            print("\n2. 检查WebSocket连接...")
            ws_connected = page.evaluate('''() => {
                return typeof socket !== 'undefined' && socket && socket.readyState === WebSocket.OPEN;
            }''')
            print(f"   WebSocket状态: {'已连接' if ws_connected else '未连接'}")
            if ws_connected:
                print("   ✓ WebSocket连接成功")
            else:
                print("   ✗ WebSocket连接失败")
            
            # 3. 检查IP显示
            print("\n3. 检查IP显示...")
            local_ip = page.locator('#local-ip')
            ip_text = local_ip.text_content()
            print(f"   IP显示内容: {ip_text}")
            
            if '127.0.0.1' in ip_text and '正在获取' not in ip_text:
                print("   ✗ IP获取失败，显示127.0.0.1")
                # 尝试手动触发IP获取
                page.evaluate('getLocalIP()')
                page.wait_for_timeout(2000)
                ip_text_after = local_ip.text_content()
                print(f"   手动触发后IP: {ip_text_after}")
                if '127.0.0.1' not in ip_text_after:
                    print("   ✓ 手动触发IP获取成功")
                else:
                    print("   ✗ 手动触发仍失败")
            elif '正在获取' in ip_text:
                print("   ⚠️ 仍在获取IP中...")
                page.wait_for_timeout(3000)
                ip_text_after = local_ip.text_content()
                print(f"   等待后IP: {ip_text_after}")
            else:
                print("   ✓ IP获取成功")
            
            # 4. 检查状态栏
            print("\n4. 检查状态栏...")
            device_name = page.locator('#device-name')
            status_text = device_name.text_content()
            print(f"   状态栏文本: {status_text}")
            
            if "等待手机连接" in status_text:
                print("   ✓ 状态栏显示等待连接（正确状态）")
            elif "连接中" in status_text:
                print("   ✓ 状态栏显示连接中")
            elif "已连接" in status_text or "手机" in status_text:
                print("   ✓ 状态栏显示已连接")
            else:
                print(f"   ⚠️ 状态栏状态未知: {status_text}")
            
            # 5. 检查控制台日志
            print("\n5. 检查控制台日志...")
            ip_logs = [log for log in console_logs if 'IP' in log or 'network' in log.lower() or 'socket' in log.lower()]
            if ip_logs:
                print("   相关日志:")
                for log in ip_logs[:10]:
                    print(f"     {log}")
            else:
                print("   无相关日志")
            
            # 6. 测试模拟连接状态
            print("\n6. 测试状态更新...")
            page.evaluate('updateConnectionStatus("connecting")')
            page.wait_for_timeout(500)
            status_connecting = device_name.text_content()
            print(f"   连接中状态: {status_connecting}")
            
            page.evaluate('updateConnectionStatus("connected", "测试手机")')
            page.wait_for_timeout(500)
            status_connected = device_name.text_content()
            print(f"   已连接状态: {status_connected}")
            
            page.evaluate('updateConnectionStatus("disconnected")')
            page.wait_for_timeout(500)
            status_disconnected = device_name.text_content()
            print(f"   断开状态: {status_disconnected}")
            
            # 7. 测试网络信息请求
            print("\n7. 测试网络信息接口...")
            network_info = page.evaluate('''async () => {
                return new Promise((resolve) => {
                    if (!socket || socket.readyState !== WebSocket.OPEN) {
                        resolve({ error: 'WebSocket未连接' });
                        return;
                    }
                    const reqId = crypto.randomUUID();
                    const timeout = setTimeout(() => {
                        resolve({ error: '超时' });
                    }, 3000);
                    
                    pending.set(reqId, {
                        resolve: (d) => {
                            clearTimeout(timeout);
                            pending.delete(reqId);
                            resolve(d);
                        },
                        reject: (e) => {
                            clearTimeout(timeout);
                            pending.delete(reqId);
                            resolve({ error: e });
                        }
                    });
                    
                    socket.send(JSON.stringify({ req_id: reqId, type: 'get_network_info' }));
                });
            }''')
            print(f"   网络信息响应: {network_info}")
            if network_info and network_info.get('hotspot_ip'):
                print(f"   ✓ 获取到热点IP: {network_info['hotspot_ip']}")
            else:
                print("   ✗ 未获取到热点IP")
            
            print("\n" + "="*60)
            print("测试完成！")
            print("="*60)
            
            # 保持浏览器打开以便观察
            page.wait_for_timeout(5000)
            
            return True
            
        except Exception as e:
            print(f"\n测试异常: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            browser.close()

if __name__ == '__main__':
    success = test_desktop_full()
    sys.exit(0 if success else 1)
