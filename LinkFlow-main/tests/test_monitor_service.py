"""
模块D: MonitorService 单元测试
覆盖: get_screen_snapshot, get_system_stats
"""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestGetSystemStats(unittest.TestCase):
    def test_get_system_stats_returns_required_fields(self):
        """UT-MS-01: 返回结构完整"""
        from core.monitor_service import MonitorService
        stats = MonitorService.get_system_stats()
        self.assertIn("cpu_percent", stats)
        self.assertIn("memory_percent", stats)
        self.assertIn("os_info", stats)


class TestGetScreenSnapshot(unittest.TestCase):
    @patch("core.monitor_service.Image")
    @patch("core.monitor_service.ImageGrab")
    def test_snapshot_returns_base64_png(self, mock_grab, mock_image):
        """UT-MS-02: 返回 base64 PNG"""
        # 创建带属性的 mock screenshot
        mock_screenshot = MagicMock()
        mock_screenshot.width = 1920
        mock_screenshot.height = 1080
        mock_grab.return_value = mock_screenshot

        from core.monitor_service import MonitorService
        result = MonitorService.get_screen_snapshot()
        self.assertIn("data_b64", result)
        self.assertIn("timestamp", result)
        self.assertEqual(result["width"], 1920)
        self.assertEqual(result["height"], 1080)
        # PNG base64 以 iVBOR 开头
        self.assertTrue(result["data_b64"].startswith("iVBOR"))

    @patch("core.monitor_service.ImageGrab")
    @patch("core.monitor_service.Image")
    def test_snapshot_returns_timestamp(self, mock_image, mock_grab):
        """UT-MS-02b: 包含时间戳"""
        mock_screenshot = MagicMock()
        mock_screenshot.width = 1920
        mock_screenshot.height = 1080
        mock_grab.return_value = mock_screenshot

        import time
        from core.monitor_service import MonitorService
        before = int(time.time())
        result = MonitorService.get_screen_snapshot()
        after = int(time.time())
        self.assertTrue(before <= result["timestamp"] <= after)

    @patch("core.monitor_service.ImageGrab")
    @patch("core.monitor_service.Image")
    def test_snapshot_grab_raises_returns_error(self, mock_image, mock_grab):
        """UT-MS-E01: ImageGrab.grab 抛出异常时返回错误"""
        mock_grab.side_effect = Exception("capture failed")
        from core.monitor_service import MonitorService
        result = MonitorService.get_screen_snapshot()
        self.assertIn("error", result)
        self.assertEqual(result["error"], "SCREENSHOT_FAIL")

    def test_snapshot_pillow_not_installed(self):
        """UT-MS-E01b: Pillow 未安装时返回 Unavailable"""
        import core.monitor_service as msm
        orig_imagegrab = msm.ImageGrab
        orig_image = msm.Image
        msm.ImageGrab = None
        msm.Image = None
        try:
            from core.monitor_service import MonitorService
            result = MonitorService.get_screen_snapshot()
            self.assertIn("error", result)
            self.assertEqual(result["error"], "SCREENSHOT_UNAVAILABLE")
        finally:
            msm.ImageGrab = orig_imagegrab
            msm.Image = orig_image


class TestExecuteControlCommand(unittest.TestCase):
    def test_execute_returns_bool(self):
        """command 为已知值时返回 bool"""
        from core.monitor_service import MonitorService
        result = MonitorService.execute_control_command("mute")
        self.assertIsInstance(result, bool)


if __name__ == "__main__":
    unittest.main()
