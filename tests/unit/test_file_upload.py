"""文件上传功能单元测试"""
import os
import sys
import zlib
import base64
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src", "python", "linkflow"))

from core.file_uploader import FileUploader


class TestFileUploader(unittest.TestCase):
    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.upload_dir = tempfile.mkdtemp()
        self.uploader = FileUploader(temp_dir=self.temp_dir, upload_dir=self.upload_dir)
    
    def tearDown(self):
        """清理测试环境"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        shutil.rmtree(self.upload_dir, ignore_errors=True)
    
    def test_upload_init(self):
        """测试初始化上传会话"""
        result = self.uploader.init_upload("test.txt", 1024, 123456789)
        self.assertEqual(result["status"], "ok")
        self.assertIn("session_id", result)
        self.assertTrue(len(result["session_id"]) > 0)
    
    def test_upload_chunk(self):
        """测试写入上传分片"""
        # 初始化上传
        init_result = self.uploader.init_upload("test_chunk.txt", 100, 0)
        session_id = init_result["session_id"]
        
        # 写入分片
        test_data = b"Hello World"
        data_b64 = base64.b64encode(test_data).decode("ascii")
        result = self.uploader.write_chunk(session_id, 0, data_b64)
        
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["written"], len(test_data))
        self.assertEqual(result["received"], len(test_data))
    
    def test_upload_commit_success(self):
        """测试成功提交上传"""
        # 准备测试数据
        test_content = b"Test file content for upload"
        crc32 = zlib.crc32(test_content) & 0xFFFFFFFF
        
        # 初始化上传
        init_result = self.uploader.init_upload("test_commit.txt", len(test_content), crc32)
        session_id = init_result["session_id"]
        
        # 写入完整数据
        data_b64 = base64.b64encode(test_content).decode("ascii")
        self.uploader.write_chunk(session_id, 0, data_b64)
        
        # 提交上传
        commit_result = self.uploader.commit_upload(session_id)
        
        self.assertEqual(commit_result["status"], "ok")
        self.assertIn("path", commit_result)
        
        # 验证文件内容
        final_path = commit_result["path"]
        with open(final_path, "rb") as f:
            content = f.read()
        self.assertEqual(content, test_content)
    
    def test_upload_commit_incomplete(self):
        """测试提交不完整的上传"""
        init_result = self.uploader.init_upload("test_incomplete.txt", 100, 0)
        session_id = init_result["session_id"]
        
        # 只写入部分数据
        test_data = b"Partial"
        data_b64 = base64.b64encode(test_data).decode("ascii")
        self.uploader.write_chunk(session_id, 0, data_b64)
        
        # 尝试提交
        commit_result = self.uploader.commit_upload(session_id)
        self.assertEqual(commit_result["status"], "error")
        self.assertEqual(commit_result["message"], "INCOMPLETE_UPLOAD")
    
    def test_upload_commit_crc_mismatch(self):
        """测试 CRC 校验失败"""
        test_content = b"Test content"
        wrong_crc = 999999999  # 故意使用错误的 CRC
        
        init_result = self.uploader.init_upload("test_crc.txt", len(test_content), wrong_crc)
        session_id = init_result["session_id"]
        
        data_b64 = base64.b64encode(test_content).decode("ascii")
        self.uploader.write_chunk(session_id, 0, data_b64)
        
        commit_result = self.uploader.commit_upload(session_id)
        self.assertEqual(commit_result["status"], "error")
        self.assertEqual(commit_result["message"], "CRC_MISMATCH")
    
    def test_upload_cancel(self):
        """测试取消上传"""
        init_result = self.uploader.init_upload("test_cancel.txt", 100, 0)
        session_id = init_result["session_id"]
        
        result = self.uploader.cancel_upload(session_id)
        self.assertEqual(result["status"], "ok")
        
        # 验证会话已被移除
        self.assertIsNone(self.uploader.get_session_status(session_id))
    
    def test_get_session_status(self):
        """测试获取会话状态"""
        init_result = self.uploader.init_upload("test_status.txt", 100, 0)
        session_id = init_result["session_id"]
        
        status = self.uploader.get_session_status(session_id)
        self.assertIsNotNone(status)
        self.assertEqual(status["session_id"], session_id)
        self.assertEqual(status["filename"], "test_status.txt")
        
        # 验证不存在的会话
        self.assertIsNone(self.uploader.get_session_status("nonexistent"))
    
    def test_filename_collision(self):
        """测试文件名冲突处理"""
        test_content = b"Content"
        crc32 = zlib.crc32(test_content) & 0xFFFFFFFF
        
        # 第一次上传
        init_result1 = self.uploader.init_upload("same_name.txt", len(test_content), crc32)
        self.uploader.write_chunk(init_result1["session_id"], 0, base64.b64encode(test_content).decode())
        result1 = self.uploader.commit_upload(init_result1["session_id"])
        
        # 第二次上传同名文件
        init_result2 = self.uploader.init_upload("same_name.txt", len(test_content), crc32)
        self.uploader.write_chunk(init_result2["session_id"], 0, base64.b64encode(test_content).decode())
        result2 = self.uploader.commit_upload(init_result2["session_id"])
        
        # 验证两个文件都存在且路径不同
        self.assertNotEqual(result1["path"], result2["path"])
        self.assertTrue(os.path.exists(result1["path"]))
        self.assertTrue(os.path.exists(result2["path"]))

    def test_upload_commit_to_target_path(self):
        """测试上传文件应提交到指定目标目录"""
        test_content = b"Target path content"
        crc32 = zlib.crc32(test_content) & 0xFFFFFFFF
        target_dir = tempfile.mkdtemp(dir=self.upload_dir)
        try:
            init_result = self.uploader.init_upload(
                "target_path.txt",
                len(test_content),
                crc32,
                target_path=target_dir,
            )
            session_id = init_result["session_id"]
            self.uploader.write_chunk(session_id, 0, base64.b64encode(test_content).decode("ascii"))

            commit_result = self.uploader.commit_upload(session_id)

            self.assertEqual(commit_result["status"], "ok")
            self.assertTrue(commit_result["path"].startswith(target_dir))
            self.assertTrue(os.path.exists(commit_result["path"]))
        finally:
            import shutil
            shutil.rmtree(target_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
