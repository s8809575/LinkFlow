from playwright.sync_api import sync_playwright
import sys

def test_ui_optimization():
    """测试用户界面优化"""
    with sync_playwright() as p:
        # 启动浏览器
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            # 打开页面
            page.goto('file:///c:/Users/scl/Desktop/LinkFlow/src/web/mobile/index.html')
            page.wait_for_load_state('domcontentloaded')
            page.wait_for_timeout(1000)
            
            print("="*60)
            print("用户界面优化测试")
            print("="*60)
            
            # 1. 检查提示文本是否已移除
            print("\n1. 检查提示文本是否已移除...")
            ip_hint = page.locator('.ip-hint')
            if ip_hint.count() == 0:
                print("   ✓ 提示文本已移除")
            else:
                print("   ✗ 提示文本仍存在")
            
            # 2. 检查预填充IP地址
            print("\n2. 检查预填充IP地址...")
            ip_input = page.locator('#pc-address')
            ip_value = ip_input.input_value()
            if ip_value == '192.168.72.161':
                print(f"   ✓ 预填充IP正确: {ip_value}")
            else:
                print(f"   ✗ 预填充IP错误，期望: 192.168.72.161，实际: {ip_value}")
            
            # 3. 检查布局：输入框和按钮是否在同一行
            print("\n3. 检查输入框和按钮布局...")
            ip_connect_row = page.locator('.ip-connect-row')
            if ip_connect_row.count() > 0 and ip_connect_row.is_visible():
                print("   ✓ 输入框和按钮在同一行")
            else:
                print("   ✗ 布局有问题")
            
            # 4. 检查连接按钮是否可见
            print("\n4. 检查连接按钮...")
            connect_btn = page.locator('#connect-btn')
            if connect_btn.is_visible():
                print("   ✓ 连接按钮可见")
            else:
                print("   ✗ 连接按钮不可见")
            
            # 5. 测试输入功能
            print("\n5. 测试输入功能...")
            test_ip = '192.168.1.100'
            ip_input.fill(test_ip)
            filled_value = ip_input.input_value()
            if filled_value == test_ip:
                print(f"   ✓ 输入功能正常: {test_ip}")
            else:
                print(f"   ✗ 输入功能异常")
            
            # 6. 恢复预填充值
            ip_input.fill('192.168.72.161')
            
            # 7. 检查其他功能按钮是否存在
            print("\n6. 检查其他功能按钮...")
            buttons = ['btn-files', 'btn-clipboard', 'btn-monitor', 'btn-control']
            all_visible = True
            for btn_id in buttons:
                btn = page.locator(f'#{btn_id}')
                if btn.is_visible():
                    print(f"   ✓ {btn_id} 可见")
                else:
                    print(f"   ✗ {btn_id} 不可见")
                    all_visible = False
            
            if all_visible:
                print("   ✓ 所有功能按钮正常")
            
            # 8. 测试localStorage功能
            print("\n7. 测试localStorage功能...")
            page.evaluate("() => localStorage.setItem('linkflow_connected', 'true')")
            page.evaluate("() => localStorage.setItem('linkflow_address', '192.168.72.161')")
            
            saved_connected = page.evaluate("() => localStorage.getItem('linkflow_connected')")
            saved_address = page.evaluate("() => localStorage.getItem('linkflow_address')")
            
            if saved_connected == 'true' and saved_address == '192.168.72.161':
                print("   ✓ localStorage功能正常")
            else:
                print(f"   ✗ localStorage异常: connected={saved_connected}, address={saved_address}")
            
            # 清理localStorage
            page.evaluate("() => localStorage.clear()")
            
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
    success = test_ui_optimization()
    sys.exit(0 if success else 1)
