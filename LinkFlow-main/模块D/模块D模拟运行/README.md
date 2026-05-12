# 模块D 模拟运行指南

无需手机端 App、无需其他模块，用本文件夹的脚本直接演示模块D所有功能。

---

## 前提条件

### 1. 安装依赖

```bash
cd LinkFlow-main
pip install -r requirements.txt
```

### 2. 启动 LinkFlow 服务

```bash
cd LinkFlow-main
python main.py
```

启动后会看到类似输出：

```
[*] RPC 服务已就绪
    端口: 8089
    pairing_id: <UUID>
    key_b64: <BASE64>
[*] mDNS 已广播: _companion._tcp.local.
[*] 剪贴板监控服务已就绪
[*] 前端网桥已就绪: ws://localhost:8766

   LinkFlow 服务已就绪
   端口: 5000
```

**记住 `pairing_id` 和 `key_b64`，演示客户端需要用到。**

![image-20260512211315060](C:\Users\Mandy\AppData\Roaming\Typora\typora-user-images\image-20260512211315060.png)

---

## 运行演示脚本

### 方式一：手动设置配对信息

复制 main.py 输出的 `pairing_id` 和 `key_b64`，运行：

```bash
cd "LinkFlow-main/模块D模拟运行"
set LINKFLOW_PAIRING_ID=<main.py输出的ID>
set LINKFLOW_PAIRING_KEY_B64=<main.py输出的密钥>
python 演示客户端.py
```

### 方式二：直接运行（会自动生成配对信息）

脚本会尝试用自动生成的随机密钥配对（注意：这会因密钥不匹配而失败，仅演示连接过程）。

**推荐方式**：先从 main.py 复制配对信息：

```bash
# Windows CMD
set PAIRING_ID=从main.py复制
set PAIRING_KEY=从main.py复制
python 演示客户端.py
```

---

## 演示内容

脚本会按顺序测试：

| 步骤 | 方法 | 说明 |
|------|------|------|
| 1 | `system.stats` | CPU/内存/系统信息 |
| 2 | `clipboard.get` | 读取当前剪贴板 |
| 3 | `screen.snapshot` | 截取屏幕并显示尺寸 |
| 4 | `audit.query` | 查询审计日志 |
| 5 | `file.upload_init/chunk/commit` | 完整上传流程（自动创建临时文件） |
| 6 | `system.control` | 执行静音指令（真实执行！） |

---

![image-20260512211422497](C:\Users\Mandy\AppData\Roaming\Typora\typora-user-images\image-20260512211422497.png)

![image-20260512211443963](C:\Users\Mandy\AppData\Roaming\Typora\typora-user-images\image-20260512211443963.png)

![image-20260512211507678](C:\Users\Mandy\AppData\Roaming\Typora\typora-user-images\image-20260512211507678.png)

## 常见问题

**Q: 脚本报错 "连接被拒绝"**

> 确保 main.py 正在运行，且端口 8089 未被占用。

**Q: 配对失败**

> main.py 每次启动会生成新的 pairing_id 和 key_b64，需要从 main.py 输出中复制最新的值。

**Q: screen.snapshot 返回 SCREENSHOT_UNAVAILABLE**
> Pillow 未安装，执行 `pip install Pillow`。

**Q: clipboard.get 返回空或报错**
> pywin32 未安装或无权限，执行 `pip install pywin32`。

**Q: system.control 不想真的执行静音**
> 打开 `演示客户端.py`，找到第 6 步，注释掉或删除该段代码。

---

## 文件说明

| 文件 | 说明 |
|------|------|
| `演示客户端.py` | Python RPC 客户端，测试所有模块D新增接口 |
