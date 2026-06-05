from playwright.sync_api import sync_playwright
import sys
import time

def test_desktop_network():
    """测试电脑端网络连接和IP显示"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        console_logs = []
        page.on('console', lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        
        try:
            # 打开电脑端页面
            page.goto('http://localhost:8766/desktop')
            page.wait_for_load_state('domcontentloaded')
            page.wait_for_timeout(5000)  # 等待5秒
            
            print("="*60)
            print("电脑端网络连接测试")
            print("="*60)
            
            # 1. 检查页面加载
            print("\n1. 检查页面加载...")
            header = page.locator('.header-bar')
            if header.is_visible():
                print("   ✓ 页面加载成功")
            else:
                print("   ✗ 页面加载失败")
                return False
            
            # 2. 检查WebSocket连接
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
            
            if '127.0.0.1' not in ip_text or '正在获取' not in ip_text:
                print("   ✓ IP获取成功")
            else:
                print("   ✗ IP显示为127.0.0.1或正在获取")
                
            # 4. 检查状态栏
            print("\n4. 检查状态栏...")
            device_name = page.locator('#device-name')
            status_text = device_name.text_content()
            print(f"   状态栏文本: {status_text}")
            
            if "等待手机连接" in status_text:
                print("   ✓ 状态栏显示正确（等待手机连接）")
            else:
                print(f"   ⚠️ 状态栏状态: {status_text}")
            
            # 5. 检查控制台日志
            print("\n5. 检查控制台日志...")
            relevant_logs = [log for log in console_logs if 'IP' in log or 'socket' in log.lower() or 'connect' in log.lower()]
            if relevant_logs:
                print("   相关日志:")
                for log in relevant_logs[:5]:
                    print(f"     {log}")
            else:
                print("   无相关日志")
            
            # 6. 测试网络信息接口
            print("\n6. 测试网络信息接口...")
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
            
            # 7. 测试状态更新
            print("\n7. 测试状态更新...")
            page.evaluate('updateConnectionStatus("connected", "测试手机")')
            page.wait_for_timeout(500)
            status_connected = device_name.text_content()
            print(f"   连接状态: {status_connected}")
            
            if "测试手机" in status_connected:
                print("   ✓ 连接状态更新成功")
            else:
                print("   ✗ 连接状态更新失败")
            
            # 保持浏览器打开
            page.wait_for_timeout(5000)
            
            print("\n" + "="*60)
            print("测试完成！")
            print("="*60)
            
            return True
            
        except Exception as e:
            print(f"\n测试异常: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            browser.close()

if __name__ == '__main__':
    success = test_desktop_network()
    sys.exit(0 if success else 1)
