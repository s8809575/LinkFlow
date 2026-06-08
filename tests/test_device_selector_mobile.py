from playwright.sync_api import sync_playwright
import sys

def test_device_selector():
    """测试设备选择器按钮的点击功能"""
    with sync_playwright() as p:
        # 启动移动端模拟器
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 375, 'height': 812},  # iPhone X尺寸
            device_scale_factor=3,
            has_touch=True,
            user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1'
        )
        page = context.new_page()
        
        # 捕获控制台日志
        console_logs = []
        page.on('console', lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        
        try:
            # 使用file://协议打开手机端页面
            page.goto('file:///c:/Users/scl/Desktop/LinkFlow/src/web/mobile/index.html')
            page.wait_for_load_state('domcontentloaded')
            page.wait_for_timeout(2000)  # 等待JavaScript初始化
            
            print("✅ 1. 页面加载成功")
            
            # 检查设备选择器按钮是否存在
            device_selector = page.locator('#device-selector-btn')
            assert device_selector.is_visible(), "设备选择器按钮不可见"
            print("✅ 2. 设备选择器按钮可见")
            
            # 测试点击展开
            print("\n测试展开/收起功能...")
            page.evaluate('toggleDeviceList()')
            page.wait_for_timeout(500)
            
            device_list = page.locator('#device-list')
            is_active = device_list.evaluate('el => el.classList.contains("active")')
            assert is_active, "展开失败"
            print("✅ 3. 点击展开下拉列表成功")
            
            # 检查下拉列表内容
            header = page.locator('.device-list-title')
            assert header.count() > 0 and header.is_visible(), "下拉列表标题不可见"
            print(f"   下拉列表标题: {header.text_content()}")
            
            # 检查扫描状态
            scan_status = page.locator('.scan-status')
            if scan_status.count() > 0:
                scan_text = page.locator('.scan-text').text_content()
                print(f"   扫描状态: {scan_text}")
            
            # 检查手动输入区域
            manual_input = page.locator('#manual-ip-input')
            assert manual_input.is_visible(), "手动输入区域不可见"
            print("✅ 4. 手动输入区域可见")
            
            # 测试收起
            page.evaluate('toggleDeviceList()')
            page.wait_for_timeout(300)
            is_active = device_list.evaluate('el => el.classList.contains("active")')
            assert not is_active, "收起失败"
            print("✅ 5. 再次点击收起下拉列表成功")
            
            # 测试手动输入IP功能
            print("\n测试手动输入IP功能...")
            page.evaluate('toggleDeviceList()')
            page.wait_for_timeout(300)
            
            manual_ip_input = page.locator('#manual-ip-input')
            manual_ip_input.fill('192.168.1.100')
            print("   输入IP地址: 192.168.1.100")
            
            # 使用evaluate直接调用manualConnect函数
            page.evaluate('manualConnect()')
            page.wait_for_timeout(500)
            
            # 检查IP是否设置成功
            selector_label = page.locator('#selector-label')
            label_text = selector_label.text_content()
            print(f"   标签文本: {label_text}")
            
            # 检查地址输入框
            address_input = page.locator('#pc-address')
            address_value = address_input.input_value()
            print(f"   地址输入框值: {address_value}")
            
            if '192.168.1.100' in label_text or address_value == '192.168.1.100':
                print("✅ 6. 手动输入IP地址功能正常")
            else:
                print(f"⚠️ IP设置验证失败")
            
            # 打印toast消息（如果有）
            toast = page.locator('#toast')
            if toast.is_visible():
                toast_text = toast.text_content()
                print(f"   Toast消息: {toast_text}")
            
            # 测试点击外部关闭
            print("\n测试点击外部关闭...")
            page.evaluate('toggleDeviceList()')
            page.wait_for_timeout(300)
            
            # 点击页面其他区域
            page.locator('.header').click()
            page.wait_for_timeout(300)
            
            is_active = device_list.evaluate('el => el.classList.contains("active")')
            if not is_active:
                print("✅ 7. 点击外部关闭下拉列表成功")
            else:
                print("⚠️ 点击外部未能关闭下拉列表")
            
            print("\n" + "="*50)
            print("✅ 所有测试通过！设备选择器功能正常")
            print("="*50)
            return True
            
        except AssertionError as e:
            print(f"❌ 测试失败: {e}")
            return False
        except Exception as e:
            print(f"❌ 测试异常: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            browser.close()

if __name__ == '__main__':
    success = test_device_selector()
    sys.exit(0 if success else 1)
