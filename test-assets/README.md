# test-assets

## 内容
- mock/module_mocks.py：四模块契约 mock。
- fixtures/*.json：固定输入输出样例。
- smoke/run_smoke.py：合并前一键冒烟。

## 运行
```bash
python test-assets/smoke/run_smoke.py --fixtures test-assets/fixtures --src-root .
```
