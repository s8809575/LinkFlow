"""
模块D: UploadService 单元测试
覆盖: create_session, receive_chunk, commit_session, cancel_session, session过期
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.upload_service import UploadService


class TestUploadServiceCreate(unittest.TestCase):
    def setUp(self):
        UploadService._sessions.clear()

    def tearDown(self):
        UploadService._sessions.clear()

    def test_create_session_returns_uuid(self):
        """UT-UC-01: create_session 正常创建会话"""
        with tempfile.TemporaryDirectory() as tmp:
            dest = os.path.join(tmp, "test.bin")
            uid = UploadService.create_session(dest, 3)
            self.assertIsInstance(uid, str)
            self.assertEqual(len(uid), 36)
            self.assertIn(uid, UploadService._sessions)

    def test_create_session_stores_metadata(self):
        """UT-UC-01b: session 元数据正确"""
        with tempfile.TemporaryDirectory() as tmp:
            dest = os.path.join(tmp, "test.bin")
            uid = UploadService.create_session(dest, 5)
            s = UploadService._sessions[uid]
            self.assertEqual(s["path"], dest)
            self.assertEqual(s["total_chunks"], 5)
            self.assertEqual(len(s["received"]), 0)
            self.assertIn("created_at", s)

    def test_create_session_zero_chunks_raises(self):
        """UT-UC-E01: total_chunks=0 抛出异常"""
        with tempfile.TemporaryDirectory() as tmp:
            dest = os.path.join(tmp, "test.bin")
            with self.assertRaises(ValueError) as ctx:
                UploadService.create_session(dest, 0)
            self.assertEqual(str(ctx.exception), "INVALID_TOTAL_CHUNKS")

    def test_create_session_negative_chunks_raises(self):
        """UT-UC-E02: total_chunks=-1 抛出异常"""
        with tempfile.TemporaryDirectory() as tmp:
            dest = os.path.join(tmp, "test.bin")
            with self.assertRaises(ValueError) as ctx:
                UploadService.create_session(dest, -1)
            self.assertEqual(str(ctx.exception), "INVALID_TOTAL_CHUNKS")

    def test_create_session_path_not_allowed(self):
        """UT-UC-E03: 路径非法时抛出 PATH_NOT_ALLOWED"""
        with tempfile.TemporaryDirectory() as tmp:
            orig = os.environ.get("LINKFLOW_ALLOWED_ROOTS")
            os.environ["LINKFLOW_ALLOWED_ROOTS"] = tmp
            try:
                with self.assertRaises(ValueError) as ctx:
                    UploadService.create_session("/etc/evil.bin", 1)
                self.assertEqual(str(ctx.exception), "PATH_NOT_ALLOWED")
            finally:
                if orig is None:
                    os.environ.pop("LINKFLOW_ALLOWED_ROOTS", None)
                else:
                    os.environ["LINKFLOW_ALLOWED_ROOTS"] = orig


class TestUploadServiceReceive(unittest.TestCase):
    def setUp(self):
        UploadService._sessions.clear()

    def tearDown(self):
        UploadService._sessions.clear()

    def test_receive_single_chunk(self):
        """UT-UC-02: receive_chunk 正常接收一个分块"""
        with tempfile.TemporaryDirectory() as tmp:
            dest = os.path.join(tmp, "test.bin")
            uid = UploadService.create_session(dest, 3)
            ok = UploadService.receive_chunk(uid, 0, b"chunk0")
            self.assertTrue(ok)
            self.assertIn(0, UploadService._sessions[uid]["received"])
            self.assertEqual(UploadService._sessions[uid]["chunk_sizes"][0], 6)

    def test_receive_multiple_chunks(self):
        """UT-UC-02b: 接收多个不同分块"""
        with tempfile.TemporaryDirectory() as tmp:
            dest = os.path.join(tmp, "test.bin")
            uid = UploadService.create_session(dest, 3)
            UploadService.receive_chunk(uid, 0, b"aaa")
            UploadService.receive_chunk(uid, 1, b"bbb")
            UploadService.receive_chunk(uid, 2, b"ccc")
            s = UploadService._sessions[uid]
            self.assertEqual(len(s["received"]), 3)
            self.assertEqual(s["received"], {0, 1, 2})

    def test_receive_chunk_invalid_index_negative(self):
        """UT-UC-E05: chunk_index 负数拒绝"""
        with tempfile.TemporaryDirectory() as tmp:
            uid = UploadService.create_session(os.path.join(tmp, "t.bin"), 3)
            ok = UploadService.receive_chunk(uid, -1, b"data")
            self.assertFalse(ok)

    def test_receive_chunk_invalid_index_too_large(self):
        """UT-UC-E05: chunk_index >= total_chunks 拒绝"""
        with tempfile.TemporaryDirectory() as tmp:
            uid = UploadService.create_session(os.path.join(tmp, "t.bin"), 3)
            ok = UploadService.receive_chunk(uid, 3, b"data")
            self.assertFalse(ok)

    def test_receive_chunk_nonexistent_session(self):
        """UT-UC-E06: 不存在的 upload_id"""
        ok = UploadService.receive_chunk("not-exist", 0, b"data")
        self.assertFalse(ok)

    def test_receive_chunk_oversized(self):
        """UT-UC-E04: 单块超 4MB 拒绝"""
        with tempfile.TemporaryDirectory() as tmp:
            uid = UploadService.create_session(os.path.join(tmp, "t.bin"), 2)
            large_data = b"x" * (UploadService.MAX_CHUNK_SIZE + 1)
            ok = UploadService.receive_chunk(uid, 0, large_data)
            self.assertFalse(ok)

    def test_receive_chunk_exact_max_size(self):
        """UT-UC-E04b: 单块正好 4MB 应接受"""
        with tempfile.TemporaryDirectory() as tmp:
            uid = UploadService.create_session(os.path.join(tmp, "t.bin"), 2)
            max_data = b"x" * UploadService.MAX_CHUNK_SIZE
            ok = UploadService.receive_chunk(uid, 0, max_data)
            self.assertTrue(ok)


class TestUploadServiceCommit(unittest.TestCase):
    def setUp(self):
        UploadService._sessions.clear()

    def tearDown(self):
        UploadService._sessions.clear()

    def test_commit_all_chunks_ok(self):
        """UT-UC-03: 全部块到位后 commit 成功"""
        with tempfile.TemporaryDirectory() as tmp:
            dest = os.path.join(tmp, "test.bin")
            uid = UploadService.create_session(dest, 3)
            UploadService.receive_chunk(uid, 0, b"aaa")
            UploadService.receive_chunk(uid, 1, b"bbb")
            UploadService.receive_chunk(uid, 2, b"ccc")
            result = UploadService.commit_session(uid)
            self.assertTrue(result["ok"])
            self.assertEqual(result["path"], dest)
            with open(dest, "rb") as f:
                self.assertEqual(f.read(), b"aaabbbccc")
            self.assertIn("crc32", result)
            self.assertNotIn(uid, UploadService._sessions)

    def test_commit_incomplete_chunks(self):
        """UT-UC-E08: 只收到部分块时 commit 失败"""
        with tempfile.TemporaryDirectory() as tmp:
            dest = os.path.join(tmp, "test.bin")
            uid = UploadService.create_session(dest, 3)
            UploadService.receive_chunk(uid, 0, b"aaa")
            UploadService.receive_chunk(uid, 1, b"bbb")
            result = UploadService.commit_session(uid)
            self.assertFalse(result["ok"])
            self.assertEqual(result["error_code"], "CHUNKS_MISSING")
            self.assertEqual(result["missing"], [2])
            self.assertIn(uid, UploadService._sessions)

    def test_commit_nonexistent_session(self):
        """UT-UC-E07: commit 不存在的 session"""
        result = UploadService.commit_session("not-exist")
        self.assertFalse(result["ok"])
        self.assertEqual(result["error_code"], "SESSION_NOT_FOUND")

    def test_commit_cleans_temp_on_failure(self):
        """S3: commit 失败后 session 仍保留，可重试"""
        with tempfile.TemporaryDirectory() as tmp:
            dest = os.path.join(tmp, "test.bin")
            uid = UploadService.create_session(dest, 2)
            UploadService.receive_chunk(uid, 0, b"a")
            UploadService.receive_chunk(uid, 1, b"bb")
            import os as _os
            temp_dir = UploadService._sessions[uid]["temp_dir"]
            _os.remove(os.path.join(temp_dir, "chunk_1"))
            result = UploadService.commit_session(uid)
            self.assertFalse(result["ok"])
            self.assertIn(uid, UploadService._sessions)


class TestUploadServiceSession(unittest.TestCase):
    def setUp(self):
        UploadService._sessions.clear()

    def tearDown(self):
        UploadService._sessions.clear()

    def test_cancel_session(self):
        """UT-UC-05: cancel_session 清理临时文件"""
        with tempfile.TemporaryDirectory() as tmp:
            dest = os.path.join(tmp, "test.bin")
            uid = UploadService.create_session(dest, 2)
            UploadService.receive_chunk(uid, 0, b"a")
            temp_dir = UploadService._sessions[uid]["temp_dir"]
            UploadService.cancel_session(uid)
            self.assertNotIn(uid, UploadService._sessions)
            import os as _os
            self.assertFalse(_os.path.exists(temp_dir))

    def test_session_expires(self):
        """UT-UC-E09: session 超过 MAX_SESSION_AGE 被清理"""
        with tempfile.TemporaryDirectory() as tmp:
            uid = UploadService.create_session(os.path.join(tmp, "t.bin"), 1)
            UploadService._sessions[uid]["created_at"] = 0
            UploadService._cleanup_stale_sessions()
            self.assertNotIn(uid, UploadService._sessions)

    def test_get_session_status(self):
        """UT-UC-04: get_session_status 返回正确进度"""
        with tempfile.TemporaryDirectory() as tmp:
            dest = os.path.join(tmp, "test.bin")
            uid = UploadService.create_session(dest, 4)
            UploadService.receive_chunk(uid, 0, b"a")
            UploadService.receive_chunk(uid, 1, b"b")
            status = UploadService.get_session_status(uid)
            self.assertTrue(status["exists"])
            self.assertEqual(status["total_chunks"], 4)
            self.assertEqual(status["received_chunks"], 2)
            self.assertEqual(status["progress"], 50.0)
