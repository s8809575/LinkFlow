import os
import uuid
import tempfile
import hashlib
import zlib
import time as _time


class UploadService:
    """
    文件分片上传服务
    管理上传会话：创建、接收分块、提交合并
    """

    _sessions = {}  # upload_id -> {path, total_chunks, received, temp_dir, created_at}
    MAX_CHUNK_SIZE = 4 * 1024 * 1024  # 4MB per chunk
    MAX_SESSION_AGE = 3600             # session 1小时过期

    @staticmethod
    def create_session(dest_path: str, total_chunks: int) -> str:
        """
        初始化上传会话
        Returns: upload_id
        Raises: ValueError if path not allowed or total_chunks invalid
        """
        if total_chunks <= 0:
            raise ValueError("INVALID_TOTAL_CHUNKS")

        # 路径校验：不允许穿越到允许目录之外
        allowed_roots_str = os.getenv("LINKFLOW_ALLOWED_ROOTS", "").strip()
        allowed_roots = [r.strip() for r in allowed_roots_str.split(";") if r.strip()] if allowed_roots_str else None
        if allowed_roots:
            try:
                from core.file_service import FileService
                if not FileService.is_path_allowed(dest_path, allowed_roots):
                    raise ValueError("PATH_NOT_ALLOWED")
            except ImportError:
                pass

        upload_id = str(uuid.uuid4())
        temp_dir = tempfile.mkdtemp(prefix="linkflow_upload_")
        UploadService._sessions[upload_id] = {
            "path": dest_path,
            "total_chunks": total_chunks,
            "received": set(),
            "temp_dir": temp_dir,
            "chunk_sizes": {},
            "created_at": _time.time(),
        }
        return upload_id

    @staticmethod
    def receive_chunk(upload_id: str, chunk_index: int, data: bytes) -> bool:
        """
        接收一个分块
        Returns: True if ok
        """
        UploadService._cleanup_stale_sessions()

        session = UploadService._sessions.get(upload_id)
        if not session:
            return False

        if chunk_index < 0 or chunk_index >= session["total_chunks"]:
            return False

        if len(data) > UploadService.MAX_CHUNK_SIZE:
            return False

        temp_path = os.path.join(session["temp_dir"], f"chunk_{chunk_index}")
        try:
            with open(temp_path, "wb") as f:
                f.write(data)
            session["received"].add(chunk_index)
            session["chunk_sizes"][chunk_index] = len(data)
            return True
        except Exception:
            return False

    @staticmethod
    def commit_session(upload_id: str) -> dict:
        """
        合并所有分块，校验完整性
        Returns: {ok, error_code, path, crc32}
        """
        session = UploadService._sessions.get(upload_id)
        if not session:
            return {"ok": False, "error_code": "SESSION_NOT_FOUND"}

        if len(session["received"]) != session["total_chunks"]:
            missing = set(range(session["total_chunks"])) - session["received"]
            return {"ok": False, "error_code": "CHUNKS_MISSING", "missing": list(missing)}

        dest_path = session["path"]
        temp_dir = session["temp_dir"]

        try:
            dest_dir = os.path.dirname(dest_path)
            if dest_dir and not os.path.exists(dest_dir):
                os.makedirs(dest_dir)

            crc = 0
            with open(dest_path, "wb") as dest:
                for i in range(session["total_chunks"]):
                    chunk_path = os.path.join(temp_dir, f"chunk_{i}")
                    with open(chunk_path, "rb") as src:
                        data = src.read()
                        dest.write(data)
                        crc = zlib.crc32(data, crc) & 0xFFFFFFFF

            commit_result = {"ok": True, "path": dest_path, "crc32": crc, "size": os.path.getsize(dest_path)}

            UploadService._cleanup_session(upload_id)

            return commit_result

        except Exception as e:
            return {"ok": False, "error_code": "COMMIT_FAIL", "detail": str(e)}

    @staticmethod
    def cancel_session(upload_id: str) -> None:
        """取消上传，清理临时文件"""
        UploadService._cleanup_session(upload_id)

    @staticmethod
    def _cleanup_session(upload_id: str) -> None:
        """删除会话和临时目录"""
        session = UploadService._sessions.pop(upload_id, None)
        if session:
            import shutil
            temp_dir = session.get("temp_dir")
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

    @staticmethod
    def _cleanup_stale_sessions(max_age: int = None) -> None:
        """清理过期 session"""
        if max_age is None:
            max_age = UploadService.MAX_SESSION_AGE
        now = _time.time()
        stale = [
            uid for uid, s in UploadService._sessions.items()
            if now - s.get("created_at", 0) > max_age
        ]
        for uid in stale:
            UploadService._cleanup_session(uid)

    @staticmethod
    def get_session_status(upload_id: str) -> dict:
        """查询上传进度"""
        session = UploadService._sessions.get(upload_id)
        if not session:
            return {"exists": False}
        return {
            "exists": True,
            "path": session["path"],
            "total_chunks": session["total_chunks"],
            "received_chunks": len(session["received"]),
            "progress": len(session["received"]) / session["total_chunks"] * 100 if session["total_chunks"] > 0 else 0,
        }
