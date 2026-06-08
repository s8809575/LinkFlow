import struct
import json

class LinkFlowProtocol:
    """
    LinkFlow 自定义通信协议设计
    数据包结构:
    [Header: 1 byte (Type)] + [Length: 4 bytes (Data Size)] + [Payload: N bytes (Actual Data)]
    """
    
    # 模块一：文件桥接相关 (Type: 0x01)
    TYPE_FILE_LIST    = 0x11  # 请求/返回文件列表 [cite: 5, 26]
    TYPE_FILE_DATA    = 0x12  # 实际文件流切片数据 [cite: 6, 26]
    TYPE_FILE_CHUNK_REQ = 0x13
    
    # 模块二：剪贴板同步相关 (Type: 0x02)
    TYPE_CLIPBOARD    = 0x21  # 纯文本同步 [cite: 10, 27]
    TYPE_CLIP_IMAGE   = 0x22  # 剪贴板图片同步 [cite: 11]
    
    # 模块三：监控与仪表盘相关 (Type: 0x03)
    TYPE_SYS_STATS    = 0x31  # CPU/内存/温度等数据 [cite: 20]
    TYPE_SCREEN_SHOT  = 0x32  # 远程屏幕快照预览 [cite: 15]
    
    # 模块四：应急控制指令 (Type: 0x04)
    TYPE_CTRL_CMD     = 0x41  # 静音/息屏/重启等指令 [cite: 21]

    TYPE_HEARTBEAT    = 0x01
    TYPE_REQ_PHONE_CLIPBOARD = 0x23  # 请求手机剪贴板

    @staticmethod
    def pack(msg_type, data):
        """
        将数据打包成符合协议的二进制流
        """
        if isinstance(data, dict) or isinstance(data, list):
            # 将字典或列表转为 JSON 字符串再编码
            payload = json.dumps(data).encode('utf-8')
        elif isinstance(data, str):
            payload = data.encode('utf-8')
        else:
            payload = data  # 假设已经是二进制流（如图片或文件块）

        # 构造包头：B 代表 1 字节无符号整数，I 代表 4 字节无符号整数
        header = struct.pack('!BI', msg_type, len(payload))
        return header + payload

    @staticmethod
    def unpack_header(header_data):
        """
        解析包头，获取类型和后续数据长度
        """
        if len(header_data) < 5:
            return None, 0
        msg_type, length = struct.unpack('!BI', header_data)
        return msg_type, length
