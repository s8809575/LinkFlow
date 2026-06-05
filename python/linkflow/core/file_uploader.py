import os
import sys
import uuid
import zlib
from typing import Dict, Optional


def _get_data_dir() -> str:
    """获取数据目录：冻结环境用 exe 所在目录，开发环境用项目根目录"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.join(os.path.dirname(__file__), "..", "..")


class UploadSession:
    def __init__(self, session_id: str, filename: str, size: int, crc32: int, temp_path: str, target_path: Optional[str] = None):
        self.session_id = session_id
        self.filename = filename
        self.total_size = size
        self.expected_crc32 = crc32
        self.temp_path = temp_path
        self.target_path = target_path
        self.received_size = 0
        self.chunks_received = set()


class FileUploader:
    def __init__(self, temp_dir: str = "uploads_temp", upload_dir: str = "uploads"):
        data_root = _get_data_dir()
        self.temp_dir = os.path.join(data_root, temp_dir)
        self.upload_dir = os.path.join(data_root, upload_dir)
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.upload_dir, exist_ok=True)
        self.sessions: Dict[str, UploadSession] = {}

    def init_upload(self, filename: str, size: int, crc32: int, target_path: Optional[str] = None) -> dict:
        """初始化文件上传会话"""
        try:
            session_id = str(uuid.uuid4())
            temp_path = os.path.join(self.temp_dir, session_id + ".part")
            
            # 创建空的临时文件
            with open(temp_path, "wb") as f:
                f.truncate(size)
            
            self.sessions[session_id] = UploadSession(session_id, filename, size, crc32, temp_path, target_path=target_path)
            
            return {"status": "ok", "session_id": session_id}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def write_chunk(self, session_id: str, offset: int, data_b64: str) -> dict:
        """写入上传分片"""
        try:
            session = self.sessions.get(session_id)
            if not session:
                return {"status": "error", "message": "SESSION_NOT_FOUND"}

            # 解码 base64 数据
            import base64
            data = base64.b64decode(data_b64)
            
            # 验证偏移量
            if offset + len(data) > session.total_size:
                return {"status": "error", "message": "OFFSET_OUT_OF_BOUNDS"}

            # 写入文件
            with open(session.temp_path, "r+b") as f:
                f.seek(offset)
                f.write(data)

            session.received_size += len(data)
            session.chunks_received.add(offset)

            progress = int((session.received_size / session.total_size) * 100)
            return {
                "status": "ok",
                "session_id": session_id,
                "offset": offset,
                "written": len(data),
                "received": session.received_size,
                "total": session.total_size,
                "progress": progress
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def commit_upload(self, session_id: str) -> dict:
        """提交上传并完成文件"""
        try:
            session = self.sessions.get(session_id)
            if not session:
                return {"status": "error", "message": "SESSION_NOT_FOUND"}

            # 验证文件完整性
            if session.received_size != session.total_size:
                # 清理临时文件
                os.remove(session.temp_path)
                del self.sessions[session_id]
                return {"status": "error", "message": "INCOMPLETE_UPLOAD"}

            # 计算 CRC32 校验
            with open(session.temp_path, "rb") as f:
                crc = 0
                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    crc = zlib.crc32(chunk, crc)
                crc = crc & 0xFFFFFFFF

            if crc != session.expected_crc32:
                os.remove(session.temp_path)
                del self.sessions[session_id]
                return {"status": "error", "message": "CRC_MISMATCH", "expected": session.expected_crc32, "actual": crc}

            # 移动到最终位置
            destination_dir = session.target_path or self.upload_dir
            os.makedirs(destination_dir, exist_ok=True)
            final_path = os.path.join(destination_dir, session.filename)
            # 处理文件名冲突
            counter = 1
            while os.path.exists(final_path):
                name, ext = os.path.splitext(session.filename)
                final_path = os.path.join(destination_dir, f"{name}_{counter}{ext}")
                counter += 1
            
            os.rename(session.temp_path, final_path)
            del self.sessions[session_id]

            return {"status": "ok", "path": final_path, "size": session.total_size}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def cancel_upload(self, session_id: str) -> dict:
        """取消上传并清理"""
        try:
            session = self.sessions.get(session_id)
            if not session:
                return {"status": "error", "message": "SESSION_NOT_FOUND"}

            if os.path.exists(session.temp_path):
                os.remove(session.temp_path)
            
            del self.sessions[session_id]
            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_session_status(self, session_id: str) -> Optional[dict]:
        """获取上传会话状态"""
        session = self.sessions.get(session_id)
        if not session:
            return None
        
        return {
            "session_id": session_id,
            "filename": session.filename,
            "received": session.received_size,
            "total": session.total_size,
            "progress": int((session.received_size / session.total_size) * 100)
        }
