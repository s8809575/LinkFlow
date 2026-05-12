import os
import math

class FileService:
    """
    模块一：跨平台文件桥接
    负责磁盘目录扫描、权限校验及文件元数据提取
    """
    
    @staticmethod
    def is_path_allowed(path, allowed_roots):
        if not allowed_roots:
            return True

        try:
            target = os.path.normcase(os.path.normpath(os.path.abspath(path)))
        except Exception:
            return False

        for root in allowed_roots:
            try:
                root_abs = os.path.normcase(os.path.normpath(os.path.abspath(root)))
                if os.path.commonpath([target, root_abs]) == root_abs:
                    return True
            except Exception:
                continue

        return False

    @staticmethod
    def get_directory_info(target_path, allowed_roots=None):
        """
        获取指定路径下的文件和文件夹列表
        对应全案中的“双向目录浏览”功能
        """
        if allowed_roots is not None and not FileService.is_path_allowed(target_path, allowed_roots):
            return {"error": "PATH_NOT_ALLOWED", "path": target_path}

        if not os.path.exists(target_path):
            return {"error": "路径不存在"}
        
        try:
            items = []
            for entry in os.scandir(target_path):
                # 获取基本元数据
                info = {
                    "name": entry.name,
                    "type": "dir" if entry.is_dir() else "file",
                    "size": FileService._format_size(entry.stat().st_size) if entry.is_file() else "文件夹",
                    "mtime": entry.stat().st_mtime # 修改时间
                }
                items.append(info)
            
            # 按文件夹在前、名称升序排序
            items.sort(key=lambda x: (x['type'] != 'dir', x['name'].lower()))
            return items
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def _format_size(size_bytes):
        """将字节转换为人类可读的格式 (KB, MB, GB)"""
        if size_bytes == 0: return "0B"
        size_name = ("B", "KB", "MB", "GB", "TB")
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_name[i]}"

    @staticmethod
    def read_file_chunk(file_path, offset, chunk_size=1024*1024, allowed_roots=None):
        """
        读取文件切片（为流式下载做准备）
        对应全案中的“分块传输”
        """
        if allowed_roots is not None and not FileService.is_path_allowed(file_path, allowed_roots):
            return None

        try:
            with open(file_path, 'rb') as f:
                f.seek(offset)
                return f.read(chunk_size)
        except Exception:
            return None
