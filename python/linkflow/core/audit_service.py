import json
import time
import uuid
import os
from typing import List, Dict
from datetime import datetime


class AuditRecord:
    """审计记录类"""
    def __init__(self, ts: int, uuid: str, device: str, action: str, result: str, details: dict = None):
        self.ts = ts
        self.uuid = uuid
        self.device = device
        self.action = action
        self.result = result
        self.details = details or {}


class AuditService:
    """审计日志服务"""
    
    def __init__(self, log_dir: str = "audit_logs"):
        self.log_dir = os.path.join(os.path.dirname(__file__), "..", "..", log_dir)
        os.makedirs(self.log_dir, exist_ok=True)
        self._records: List[AuditRecord] = []
        self._load_existing_logs()
    
    def _load_existing_logs(self):
        """加载已存在的审计日志"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            log_file = os.path.join(self.log_dir, f"audit_{today}.log")
            if os.path.exists(log_file):
                with open(log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                data = json.loads(line)
                                record = AuditRecord(
                                    ts=data.get("ts", 0),
                                    uuid=data.get("uuid", ""),
                                    device=data.get("device", ""),
                                    action=data.get("action", ""),
                                    result=data.get("result", ""),
                                    details=data.get("details", {})
                                )
                                self._records.append(record)
                            except Exception:
                                pass
        except Exception:
            pass
    
    def _get_log_file_path(self) -> str:
        """获取当前日期的日志文件路径"""
        today = datetime.now().strftime("%Y-%m-%d")
        return os.path.join(self.log_dir, f"audit_{today}.log")
    
    def record(self, device: str, action: str, result: str, details: dict = None):
        """记录审计日志"""
        record = AuditRecord(
            ts=int(time.time()),
            uuid=str(uuid.uuid4()),
            device=device,
            action=action,
            result=result,
            details=details or {}
        )
        self._records.append(record)
        
        # 写入文件（追加模式）
        log_entry = {
            "ts": record.ts,
            "uuid": record.uuid,
            "device": record.device,
            "action": record.action,
            "result": record.result,
            "details": record.details
        }
        
        try:
            with open(self._get_log_file_path(), "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[!] 审计日志写入失败: {e}")
    
    def query(self, start_ts: int = None, end_ts: int = None, action_filter: str = None) -> List[dict]:
        """查询审计日志"""
        result = []
        for record in self._records:
            # 时间范围过滤
            if start_ts and record.ts < start_ts:
                continue
            if end_ts and record.ts > end_ts:
                continue
            # 动作类型过滤
            if action_filter and record.action != action_filter:
                continue
            
            result.append({
                "ts": record.ts,
                "uuid": record.uuid,
                "device": record.device,
                "action": record.action,
                "result": record.result,
                "details": record.details
            })
        
        # 按时间戳降序排列
        result.sort(key=lambda x: x["ts"], reverse=True)
        return result
    
    def get_recent(self, limit: int = 100) -> List[dict]:
        """获取最近的审计记录"""
        records = sorted(self._records, key=lambda x: x.ts, reverse=True)[:limit]
        return [{
            "ts": r.ts,
            "uuid": r.uuid,
            "device": r.device,
            "action": r.action,
            "result": r.result,
            "details": r.details
        } for r in records]
    
    def get_stats(self) -> dict:
        """获取审计统计信息"""
        if not self._records:
            return {"total_records": 0, "success_count": 0, "fail_count": 0, "actions": {}}
        
        success_count = sum(1 for r in self._records if r.result == "success")
        fail_count = sum(1 for r in self._records if r.result == "fail")
        
        action_counts = {}
        for r in self._records:
            action_counts[r.action] = action_counts.get(r.action, 0) + 1
        
        return {
            "total_records": len(self._records),
            "success_count": success_count,
            "fail_count": fail_count,
            "actions": action_counts
        }
