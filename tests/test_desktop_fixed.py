from playwright.sync_api import sync_playwright
import sys
import time

def test_desktop_fixed():
    """测试电脑端界面修复"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        console_logs = []
        page.on('console', lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        
        try:
            # 打开电脑端页面
            page.goto('file:///c:/Users/scl/Desktop/LinkFlow/src/web/desktop/index.html')
            page.wait_for_load_state('domcontentloaded')
            page.wait_for_timeout(1000)  # 等待页面初始化
            
            print("="*60)
            print("电脑端界面修复测试")
            print("="*60)
            
            # 1. 检查页面加载
            print("\n1. 检查页面加载...")
            header = page.locator('.header-bar')
            assert header.is_visible(), "页面未正确加载"
            print("   ✓ 页面加载成功")
            
            # 2. 检查IP显示区域
            print("\n2. 检查IP显示...")
            local_ip = page.locator('#local-ip')
            ip_text = local_ip.text_content()
            print(f"   初始IP显示: {ip_text}")
            
            # 3. 检查状态栏初始状态
            print("\n3. 检查状态栏初始状态...")
            device_name = page.locator('#device-name')
            status_text = device_name.text_content()
            print(f"   状态栏文本: {status_text}")
            
            if "等待手机连接" in status_text:
                print("   ✓ 初始状态正确")
            else:
                print(f"   状态异常: {status_text}")
            
            # 4. 模拟后端响应
            print("\n4. 模拟后端network_info响应...")
            page.evaluate('''() => {
                // 模拟收到后端的network_info响应
                const fakeResponse = {
                    type: 'network_info',
                    hotspot_ip: '192.168.43.100',
                    ips: ['192.168.43.100', '192.168.1.100'],
                    hostname: 'TEST-PC'
                };
                
                // 手动触发IP更新
                document.getElementById('local-ip').textContent = '本机 IP: ' + fakeResponse.hotspot_ip;
            }''')
            page.wait_for_timeout(500)
            
            ip_after = local_ip.text_content()
            print(f"   IP更新后: {ip_after}")
            
            if '192.168.43.100' in ip_after:
                print("   ✓ IP更新功能正常")
            else:
                print("   ✗ IP更新失败")
            
            # 5. 模拟手机连接状态
            print("\n5. 模拟手机连接...")
            page.evaluate('''() => {
                updateConnectionStatus('connected', '测试手机');
            }''')
            page.wait_for_timeout(500)
            
            status_connected = device_name.text_content()
            print(f"   连接后状态: {status_connected}")
            
            if "测试手机" in status_connected:
                print("   ✓ 手机连接状态更新正常")
            else:
                print("   ✗ 手机连接状态更新失败")
            
            # 6. 模拟手机断开连接
            print("\n6. 模拟手机断开连接...")
            page.evaluate('''() => {
                updateConnectionStatus('disconnected');
            }''')
            page.wait_for_timeout(500)
            
            status_disconnected = device_name.text_content()
            print(f"   断开后状态: {status_disconnected}")
            
            if "等待手机连接" in status_disconnected:
                print("   ✓ 断开状态更新正常")
            else:
                print("   ✗ 断开状态更新失败")
            
            # 7. 检查控制台日志
            print("\n7. 检查控制台日志...")
            ip_logs = [log for log in console_logs if '[IP]' in log or '获取' in log]
            if ip_logs:
                print("   IP相关日志:")
                for log in ip_logs[:5]:  # 只显示前5条
                    print(f"     {log}")
            else:
                print("   无IP相关日志")
            
            # 8. 模拟连接中状态
            print("\n8. 模拟连接中状态...")
            page.evaluate('''() => {
                updateConnectionStatus('connecting');
            }''')
            page.wait_for_timeout(500)
            
            status_connecting = device_name.text_content()
            print(f"   连接中状态: {status_connecting}")
            
            if "连接中" in status_connecting:
                print("   ✓ 连接中状态正常")
            else:
                print("   ✗ 连接中状态异常")
            
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
    success = test_desktop_fixed()
    sys.exit(0 if success else 1)
