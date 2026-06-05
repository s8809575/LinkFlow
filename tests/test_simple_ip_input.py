from playwright.sync_api import sync_playwright
import sys

def test_simple_ip_input():
    """测试简化后的手动输入IP功能"""
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
            print("简化版IP输入测试")
            print("="*60)
            
            # 测试1：页面加载
            print("\n【测试1】页面加载")
            print("✅ 页面加载成功")
            
            # 测试2：检查IP输入框存在
            print("\n【测试2】检查IP输入框")
            ip_input = page.locator('#pc-address')
            assert ip_input.is_visible(), "IP输入框不可见"
            print("✅ IP输入框可见")
            
            # 测试3：检查预填充值
            print("\n【测试3】检查预填充值")
            ip_value = ip_input.input_value()
            print(f"   预填充IP: {ip_value}")
            assert ip_value == '192.168.43.1', f"预填充值错误: {ip_value}"
            print("✅ 预填充值正确")
            
            # 测试4：输入新IP
            print("\n【测试4】输入新IP地址")
            ip_input.fill('192.168.1.100')
            new_value = ip_input.input_value()
            assert new_value == '192.168.1.100', f"输入失败: {new_value}"
            print(f"✅ 输入IP成功: {new_value}")
            
            # 测试5：检查输入框样式
            print("\n【测试5】验证输入框样式")
            input_styles = page.evaluate('''() => {
                const input = document.getElementById("pc-address");
                const styles = window.getComputedStyle(input);
                return {
                    type: input.type,
                    placeholder: input.placeholder,
                    borderRadius: styles.borderRadius,
                    fontSize: styles.fontSize
                };
            }''')
            print(f"   样式信息: {input_styles}")
            
            # 测试6：检查连接按钮
            print("\n【测试6】检查连接按钮")
            connect_btn = page.locator('#connect-btn')
            assert connect_btn.is_visible(), "连接按钮不可见"
            btn_text = connect_btn.text_content()
            print(f"   按钮文本: {btn_text}")
            print("✅ 连接按钮可见")
            
            # 测试7：检查提示文字
            print("\n【测试7】检查提示文字")
            ip_hint = page.locator('.ip-hint')
            if ip_hint.count() > 0 and ip_hint.is_visible():
                hint_text = ip_hint.text_content()
                print(f"   提示文字: {hint_text}")
                print("✅ 提示文字可见")
            
            # 测试8：检查其他功能按钮
            print("\n【测试8】检查其他功能按钮")
            btn_files = page.locator('#btn-files')
            btn_clipboard = page.locator('#btn-clipboard')
            btn_monitor = page.locator('#btn-monitor')
            btn_control = page.locator('#btn-control')
            
            assert btn_files.is_visible(), "文件按钮不可见"
            assert btn_clipboard.is_visible(), "剪贴板按钮不可见"
            assert btn_monitor.is_visible(), "监控按钮不可见"
            assert btn_control.is_visible(), "控制按钮不可见"
            print("✅ 所有功能按钮可见")
            
            # 测试9：检查状态栏
            print("\n【测试9】检查状态栏")
            conn_indicator = page.locator('#conn-indicator')
            assert conn_indicator.is_visible(), "连接指示器不可见"
            print(f"   连接状态: {conn_indicator.text_content()}")
            print("✅ 状态栏正常")
            
            # 测试10：按回车触发连接
            print("\n【测试10】测试回车触发")
            ip_input.press('Enter')
            print("✅ 回车事件已触发")
            
            # 打印控制台错误（如果有）
            errors = [log for log in console_logs if log.startswith('[error]')]
            if errors:
                print("\n⚠️ 控制台错误:")
                for error in errors:
                    print(f"  {error}")
            
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
    success = test_simple_ip_input()
    sys.exit(0 if success else 1)