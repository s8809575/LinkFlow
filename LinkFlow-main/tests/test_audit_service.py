"""
模块D: AuditService 单元测试
覆盖: log, query, 日志轮转
"""
import os
import sys
import time
import json
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.audit_service import AuditService


class TestAuditServiceLog(unittest.TestCase):
    def setUp(self):
        AuditService._log_file = tempfile.mktemp(suffix=".json")
        AuditService._memory_log.clear()

    def tearDown(self):
        AuditService._memory_log.clear()
        for f in [AuditService._log_file, AuditService._log_file + ".old"]:
            if os.path.exists(f):
                os.remove(f)

    def test_log_returns_uuid(self):
        """UT-AS-01a: log 返回 UUID"""
        uuid = AuditService.log("device1", "action1", "ok")
        self.assertIsInstance(uuid, str)
        self.assertEqual(len(uuid), 36)

    def test_log_stored_in_memory(self):
        """UT-AS-01b: 日志存入内存"""
        AuditService.log("device1", "action1", "ok")
        self.assertEqual(len(AuditService._memory_log), 1)
        entry = AuditService._memory_log[0]
        self.assertEqual(entry["device"], "device1")
        self.assertEqual(entry["action"], "action1")
        self.assertEqual(entry["result"], "ok")
        self.assertIn("ts", entry)

    def test_log_written_to_file(self):
        """UT-AS-01c: 日志追加写入文件"""
        AuditService.log("device1", "action1", "ok")
        self.assertTrue(os.path.exists(AuditService._log_file))
        with open(AuditService._log_file) as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 1)
        entry = json.loads(lines[0])
        self.assertEqual(entry["device"], "device1")

    def test_log_with_extra(self):
        """UT-AS-01d: 带 extra 字段"""
        AuditService.log("d1", "upload.init", "started", extra={"upload_id": "abc123"})
        entry = AuditService._memory_log[-1]
        self.assertEqual(entry["extra"], {"upload_id": "abc123"})


class TestAuditServiceQuery(unittest.TestCase):
    def setUp(self):
        AuditService._log_file = tempfile.mktemp(suffix=".json")
        AuditService._memory_log.clear()
        now = int(time.time())
        self.t1 = now - 100
        self.t2 = now - 50
        self.t3 = now
        for ts, dev, act, res in [
            (self.t1, "d1", "act1", "ok"),
            (self.t2, "d2", "act2", "ok"),
            (self.t3, "d3", "act3", "fail"),
        ]:
            entry = {"ts": ts, "uuid": "u", "device": dev, "action": act, "result": res}
            AuditService._memory_log.append(entry)

    def tearDown(self):
        AuditService._memory_log.clear()
        if os.path.exists(AuditService._log_file):
            os.remove(AuditService._log_file)

    def test_query_returns_all_in_window(self):
        """UT-AS-02: 查询时间窗口内所有日志"""
        results = AuditService.query(self.t1 - 10, self.t3 + 10)
        self.assertEqual(len(results), 3)

    def test_query_filters_by_time(self):
        """UT-AS-02b: 只返回窗口内记录"""
        results = AuditService.query(self.t2, self.t3)
        for r in results:
            self.assertTrue(self.t2 <= r["ts"] <= self.t3)
        self.assertEqual(len(results), 2)

    def test_query_empty_window(self):
        """UT-AS-E01: 窗口内无日志返回空"""
        results = AuditService.query(self.t3 + 100, self.t3 + 200)
        self.assertEqual(results, [])

    def test_query_respects_limit(self):
        """UT-AS-03: limit 限制条数"""
        results = AuditService.query(0, 0, limit=2)
        self.assertLessEqual(len(results), 2)

    def test_query_sorted_by_ts_descending(self):
        """UT-AS-02c: 结果按 ts 降序"""
        results = AuditService.query(0, 0)
        ts_list = [r["ts"] for r in results]
        self.assertEqual(ts_list, sorted(ts_list, reverse=True))


class TestAuditServiceRotation(unittest.TestCase):
    def setUp(self):
        AuditService._log_file = tempfile.mktemp(suffix=".json")
        AuditService._memory_log.clear()

    def tearDown(self):
        AuditService._memory_log.clear()
        for f in [AuditService._log_file, AuditService._log_file + ".old"]:
            if os.path.exists(f):
                os.remove(f)

    def test_rotation_when_file_too_large(self):
        """M2: 日志文件超过 MAX_LOG_SIZE 时轮转"""
        orig_size = AuditService.MAX_LOG_SIZE
        AuditService.MAX_LOG_SIZE = 100
        try:
            AuditService.log("d", "a", "r")
            large_extra = {"data": "x" * 200}
            AuditService.log("d", "a", "r", extra=large_extra)
            self.assertTrue(os.path.exists(AuditService._log_file + ".old"))
        finally:
            AuditService.MAX_LOG_SIZE = orig_size
