"""审计服务单元测试"""
import os
import sys
import unittest
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src", "python", "linkflow"))

from core.audit_service import AuditService


class TestAuditService(unittest.TestCase):
    def setUp(self):
        """设置测试环境"""
        self.log_dir = tempfile.mkdtemp()
        self.service = AuditService(log_dir=self.log_dir)
    
    def tearDown(self):
        """清理测试环境"""
        import shutil
        shutil.rmtree(self.log_dir, ignore_errors=True)
    
    def test_record_audit(self):
        """测试记录审计日志"""
        # 记录审计日志
        self.service.record(
            device="test_device",
            action="file.read",
            result="success",
            details={"path": "/test/file.txt"}
        )
        
        # 查询记录
        records = self.service.query()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["device"], "test_device")
        self.assertEqual(records[0]["action"], "file.read")
        self.assertEqual(records[0]["result"], "success")
        self.assertEqual(records[0]["details"]["path"], "/test/file.txt")
    
    def test_query_with_time_filter(self):
        """测试按时间范围查询"""
        # 记录多条日志
        self.service.record("device1", "action1", "success")
        time.sleep(0.2)
        mid_time = int(time.time() * 1000)  # 使用毫秒级时间戳
        time.sleep(0.2)
        self.service.record("device2", "action2", "fail")
        
        # 查询时间范围内的记录
        records = self.service.query(start_ts=mid_time // 1000)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["action"], "action2")
    
    def test_query_with_action_filter(self):
        """测试按动作类型查询"""
        self.service.record("device1", "file.read", "success")
        self.service.record("device1", "system.control", "success")
        self.service.record("device1", "file.read", "fail")
        
        # 过滤特定动作
        records = self.service.query(action_filter="file.read")
        self.assertEqual(len(records), 2)
        self.assertTrue(all(r["action"] == "file.read" for r in records))
    
    def test_get_recent(self):
        """测试获取最近记录"""
        # 记录多条日志
        for i in range(10):
            self.service.record(f"device{i}", f"action{i}", "success")
        
        # 获取最近5条
        recent = self.service.get_recent(limit=5)
        self.assertEqual(len(recent), 5)
        # 验证按时间降序排列
        timestamps = [r["ts"] for r in recent]
        self.assertEqual(timestamps, sorted(timestamps, reverse=True))
    
    def test_get_stats(self):
        """测试获取统计信息"""
        self.service.record("device1", "file.read", "success")
        self.service.record("device1", "file.read", "success")
        self.service.record("device1", "system.control", "fail")
        
        stats = self.service.get_stats()
        self.assertEqual(stats["total_records"], 3)
        self.assertEqual(stats["success_count"], 2)
        self.assertEqual(stats["fail_count"], 1)
        self.assertEqual(stats["actions"]["file.read"], 2)
        self.assertEqual(stats["actions"]["system.control"], 1)
    
    def test_empty_stats(self):
        """测试空统计信息"""
        stats = self.service.get_stats()
        self.assertEqual(stats["total_records"], 0)
        self.assertEqual(stats["success_count"], 0)
        self.assertEqual(stats["fail_count"], 0)
        self.assertEqual(stats["actions"], {})


if __name__ == "__main__":
    unittest.main()
