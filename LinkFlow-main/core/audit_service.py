import os
import uuid
import json
import time
import threading
from datetime import datetime


class AuditService:
    """
    审计日志服务
    记录操作并提供查询接口
    """

    _lock = threading.Lock()
    _memory_log = []  # 内存缓存
    _log_file = "audit_log.json"
    _max_memory_entries = 1000
    MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB，超过后轮转

    @staticmethod
    def log(device: str, action: str, result: str, extra: dict = None) -> str:
        """
        记录一条操作日志
        Returns: uuid
        """
        entry = {
            "ts": int(time.time()),
            "ts_iso": datetime.now().isoformat(),
            "uuid": str(uuid.uuid4()),
            "device": device,
            "action": action,
            "result": result,
        }
        if extra:
            entry["extra"] = extra

        with AuditService._lock:
            AuditService._memory_log.append(entry)
            if len(AuditService._memory_log) > AuditService._max_memory_entries:
                AuditService._memory_log = AuditService._memory_log[-AuditService._max_memory_entries:]

        AuditService._write_to_file(entry)
        return entry["uuid"]

    @staticmethod
    def query(start_ts: int = 0, end_ts: int = 0, limit: int = 100) -> list:
        """
        查询操作日志
        Args:
            start_ts: 开始时间戳（秒）
            end_ts: 结束时间戳（秒），0 表示到现在
            limit: 返回条数上限
        """
        if end_ts == 0:
            end_ts = int(time.time()) + 1

        with AuditService._lock:
            results = [
                entry for entry in AuditService._memory_log
                if start_ts <= entry["ts"] <= end_ts
            ]

        file_entries = AuditService._read_from_file(start_ts, end_ts)
        seen_uuids = {e["uuid"] for e in results}
        for entry in file_entries:
            if entry["uuid"] not in seen_uuids and start_ts <= entry["ts"] <= end_ts:
                results.append(entry)
                seen_uuids.add(entry["uuid"])

        results.sort(key=lambda x: x["ts"], reverse=True)
        return results[:limit]

    @staticmethod
    def _write_to_file(entry: dict) -> None:
        """追加写入日志文件，超大小则轮转"""
        try:
            log_path = AuditService._log_file
            entry_line = json.dumps(entry, ensure_ascii=False) + "\n"
            current_size = os.path.getsize(log_path) if os.path.exists(log_path) else 0
            if current_size + len(entry_line.encode("utf-8")) > AuditService.MAX_LOG_SIZE:
                try:
                    os.rename(log_path, log_path + ".old")
                except OSError:
                    pass
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(entry_line)
        except Exception:
            pass

    @staticmethod
    def _read_from_file(start_ts: int, end_ts: int) -> list:
        """从日志文件读取指定时间范围内的记录"""
        results = []
        if not os.path.exists(AuditService._log_file):
            return results
        try:
            with open(AuditService._log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        if start_ts <= entry.get("ts", 0) <= end_ts:
                            results.append(entry)
                    except json.JSONDecodeError:
                        continue
        except Exception:
            pass
        return results

    @staticmethod
    def clear() -> None:
        """清空内存和文件日志（仅用于测试）"""
        with AuditService._lock:
            AuditService._memory_log.clear()
        if os.path.exists(AuditService._log_file):
            os.remove(AuditService._log_file)
