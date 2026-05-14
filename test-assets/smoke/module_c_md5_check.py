#!/usr/bin/env python3
"""Generate deterministic module-C sample MD5 values without storing large blobs."""
import hashlib
import json
import pathlib


FIXTURE = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "module_c_transfer_samples.json"


def md5_for_size(size: int) -> str:
    pattern = bytes(((i * 31 + 7) & 255) for i in range(256))
    block = pattern * 4096
    full_patterns, remainder = divmod(size, len(pattern))
    full_blocks, extra_patterns = divmod(full_patterns, 4096)
    md5 = hashlib.md5()
    for _ in range(full_blocks):
        md5.update(block)
    md5.update(pattern * extra_patterns)
    md5.update(pattern[:remainder])
    return md5.hexdigest()


def main() -> int:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    for sample in fixture["samples"]:
        actual = md5_for_size(int(sample["size"]))
        status = "OK" if actual == sample["md5"] else "FAIL"
        print(f'{sample["name"]} size={sample["size"]} md5={actual} {status}')
        if status != "OK":
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
