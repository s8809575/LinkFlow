#!/usr/bin/env python3
"""One-click smoke test for contract validity and accidental coupling checks."""
import argparse
import json
import pathlib
import re
import sys

FIXTURE_FILES = [
    'pairing_context.json',
    'file_chunk_result.json',
    'system_stats_result.json',
]

BANNED_IMPORTS = {
    'module-A': ['module-B', 'module-C', 'module-D'],
    'module-B': ['module-A', 'module-C', 'module-D'],
    'module-C': ['module-A', 'module-B', 'module-D'],
    'module-D': ['module-A', 'module-B', 'module-C'],
}

def validate_fixtures(fixtures_dir: pathlib.Path) -> list[str]:
    errs = []
    for name in FIXTURE_FILES:
        p = fixtures_dir / name
        if not p.exists():
            errs.append(f'missing fixture: {name}')
            continue
        try:
            json.loads(p.read_text(encoding='utf-8-sig'))
        except Exception as e:
            errs.append(f'invalid json: {name}: {e}')
    return errs

def check_forbidden_imports(src_root: pathlib.Path) -> list[str]:
    errs = []
    if not src_root.exists():
        return errs
    py_files = list(src_root.rglob('*.py')) + list(src_root.rglob('*.kt'))
    for f in py_files:
        text = f.read_text(encoding='utf-8', errors='ignore')
        for module, banned in BANNED_IMPORTS.items():
            if module.lower() in str(f).lower():
                for b in banned:
                    if re.search(rf'\b{re.escape(b)}\b', text):
                        errs.append(f'forbidden coupling: {f} -> {b}')
    return errs

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--fixtures', default='test-assets/fixtures')
    parser.add_argument('--src-root', default='.')
    args = parser.parse_args()

    errs = []
    errs.extend(validate_fixtures(pathlib.Path(args.fixtures)))
    errs.extend(check_forbidden_imports(pathlib.Path(args.src_root)))

    if errs:
        print('SMOKE FAILED')
        for e in errs:
            print('-', e)
        return 1
    print('SMOKE PASSED')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
