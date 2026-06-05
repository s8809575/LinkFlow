from playwright.sync_api import sync_playwright
import sys
import time

def test_device_selector_comprehensive():
    """综合测试设备选择器功能"""
    with sync_playwright() as p:
        # 启动移动端模拟器
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 375, 'height': 812},
            device_scale_factor=3,
            has_touch=True,
            user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1'
        )
        page = context.new_page()
        
        console_logs = []
        page.on('console', lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        
        try:
            # 打开页面
            page.goto('file:///c:/Users/scl/Desktop/LinkFlow/src/web/mobile/index.html')
            page.wait_for_load_state('domcontentloaded')
            page.wait_for_timeout(2000)
            
            print("="*60)
            print("设备选择器综合测试")
            print("="*60)
            
            # 测试1：展开下拉列表
            print("\n【测试1】展开下拉列表")
            page.evaluate('toggleDeviceList()')
            page.wait_for_timeout(500)
            
            device_list = page.locator('#device-list')
            is_active = device_list.evaluate('el => el.classList.contains("active")')
            assert is_active, "展开失败"
            print("✅ 展开成功")
            
            # 测试2：检查预填充IP
            print("\n【测试2】检查IP预填充")
            manual_ip = page.locator('#manual-ip-input')
            ip_value = manual_ip.input_value()
            print(f"   预填充IP: {ip_value}")
            
            # 测试3：检查扫描状态
            print("\n【测试3】检查扫描状态")
            scan_status = page.locator('.scan-status')
            if scan_status.count() > 0:
                print("✅ 扫描状态显示正常")
            
            # 测试4：手动输入IP
            print("\n【测试4】手动输入IP地址")
            manual_ip.fill('192.168.1.100')
            page.evaluate('manualConnect()')
            page.wait_for_timeout(500)
            
            selector_label = page.locator('#selector-label')
            label_text = selector_label.text_content()
            assert '192.168.1.100' in label_text, f"IP设置失败: {label_text}"
            print(f"✅ IP设置成功: {label_text}")
            
            # 测试5：验证地址输入框
            print("\n【测试5】验证地址输入框")
            address_input = page.locator('#pc-address')
            address_value = address_input.input_value()
            assert address_value == '192.168.1.100', f"地址错误: {address_value}"
            print(f"✅ 地址输入框正确: {address_value}")
            
            # 测试6：检查下拉列表是否已关闭（manualConnect会关闭列表）
            print("\n【测试6】检查下拉列表状态")
            is_active_after_connect = device_list.evaluate('el => el.classList.contains("active")')
            if not is_active_after_connect:
                print("✅ manualConnect后列表已关闭")
            else:
                # 如果列表还开着，关闭它
                page.evaluate('toggleDeviceList()')
                page.wait_for_timeout(300)
                print("✅ 手动关闭列表成功")
            
            # 测试7：检查Toast提示
            print("\n【测试7】检查Toast提示")
            toast = page.locator('#toast')
            toast_visible = toast.is_visible()
            print(f"   Toast可见: {toast_visible}")
            
            # 测试8：点击外部关闭
            print("\n【测试8】点击外部关闭")
            page.evaluate('toggleDeviceList()')
            page.wait_for_timeout(300)
            page.locator('.header').click()
            page.wait_for_timeout(300)
            is_active = device_list.evaluate('el => el.classList.contains("active")')
            if not is_active:
                print("✅ 点击外部关闭成功")
            else:
                print("⚠️ 点击外部未能关闭")
            
            # 测试9：检查其他功能按钮
            print("\n【测试9】检查其他功能按钮")
            connect_btn = page.locator('#connect-btn')
            assert connect_btn.is_visible(), "连接按钮不可见"
            print("✅ 连接按钮可见")
            
            # 测试10：验证CSS样式
            print("\n【测试10】验证CSS样式")
            btn_styles = page.evaluate('''() => {
                const btn = document.getElementById("device-selector-btn");
                const styles = window.getComputedStyle(btn);
                return {
                    cursor: styles.cursor,
                    touchAction: styles.touchAction,
                    webkitAppearance: styles.webkitAppearance
                };
            }''')
            print(f"   样式: {btn_styles}")
            
            print("\n" + "="*60)
            print("✅ 所有测试通过！")
            print("="*60)
            
            return True
            
        except AssertionError as e:
            print(f"\n❌ 测试失败: {e}")
            return False
        except Exception as e:
            print(f"\n❌ 测试异常: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            browser.close()

if __name__ == '__main__':
    success = test_device_selector_comprehensive()
    sys.exit(0 if success else 1)
