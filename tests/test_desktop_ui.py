from playwright.sync_api import sync_playwright
import sys

def test_desktop_ui():
    """测试电脑端界面修复"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            # 打开电脑端页面
            page.goto('file:///c:/Users/scl/Desktop/LinkFlow/src/web/desktop/index.html')
            page.wait_for_load_state('domcontentloaded')
            page.wait_for_timeout(2000)  # 等待IP获取
            
            print("="*60)
            print("电脑端界面测试")
            print("="*60)
            
            # 1. 检查IP地址显示
            print("\n1. 检查IP地址显示...")
            local_ip = page.locator('#local-ip')
            ip_text = local_ip.text_content()
            print(f"   IP显示: {ip_text}")
            
            # 等待IP更新
            if "正在获取 IP" in ip_text:
                print("   等待IP获取...")
                page.wait_for_timeout(4000)  # 等待最多4秒
                ip_text = local_ip.text_content()
                print(f"   更新后IP: {ip_text}")
            
            # 2. 检查状态栏初始状态
            print("\n2. 检查状态栏初始状态...")
            device_name = page.locator('#device-name')
            status_text = device_name.text_content()
            print(f"   状态栏文本: {status_text}")
            
            if "等待手机连接" in status_text or "连接中" in status_text:
                print("   ✓ 初始状态正确")
            else:
                print(f"   ✗ 初始状态异常: {status_text}")
            
            # 3. 检查状态栏样式
            print("\n3. 检查状态栏样式...")
            status_dot = page.locator('#status-dot')
            status_class = status_dot.get_attribute('class')
            print(f"   状态点class: {status_class}")
            
            # 4. 检查连接状态容器
            print("\n4. 检查连接状态容器...")
            connection_status = page.locator('#connection-status')
            conn_class = connection_status.get_attribute('class')
            print(f"   连接状态class: {conn_class}")
            
            # 5. 检查页面元素
            print("\n5. 检查页面元素...")
            elements_to_check = [
                ('#cpu-val', 'CPU显示'),
                ('#memory-val', '内存显示'),
                ('#battery-val', '电池显示'),
                ('#device-name', '设备名称'),
                ('#local-ip', '本地IP')
            ]
            
            for selector, name in elements_to_check:
                el = page.locator(selector)
                if el.count() > 0:
                    print(f"   ✓ {name} 存在")
                else:
                    print(f"   ✗ {name} 不存在")
            
            # 6. 模拟状态更新
            print("\n6. 模拟状态更新...")
            
            # 先停止重连逻辑，避免干扰测试
            page.evaluate('''() => {
                // 临时保存原始函数
                window._originalConnect = connectToBackend;
                // 覆盖为空函数，停止重连
                connectToBackend = () => {};
            }''')
            
            page.evaluate('''() => {
                updateConnectionStatus('connected', '测试手机');
            }''')
            page.wait_for_timeout(500)
            
            status_after_connect = device_name.text_content()
            print(f"   连接后状态: {status_after_connect}")
            
            if "测试手机" in status_after_connect:
                print("   ✓ 状态更新函数正常")
            else:
                print(f"   ✗ 状态更新失败")
            
            # 7. 测试断开连接状态
            page.evaluate('''() => {
                updateConnectionStatus('disconnected');
            }''')
            page.wait_for_timeout(300)
            
            status_after_disconnect = device_name.text_content()
            print(f"   断开后状态: {status_after_disconnect}")
            
            if "等待手机连接" in status_after_disconnect:
                print("   ✓ 断开状态正确")
            else:
                print(f"   ✗ 断开状态异常")
            
            # 8. 测试连接中状态
            page.evaluate('''() => {
                updateConnectionStatus('connecting');
            }''')
            page.wait_for_timeout(300)
            
            status_connecting = device_name.text_content()
            print(f"   连接中状态: {status_connecting}")
            
            if "连接中" in status_connecting:
                print("   ✓ 连接中状态正确")
            else:
                print(f"   ✗ 连接中状态异常")
            
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
    success = test_desktop_ui()
    sys.exit(0 if success else 1)
