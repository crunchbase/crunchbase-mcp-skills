#!/usr/bin/env python3
"""Synchronize host package versions with the collection's VERSION file."""
import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='fail on a version mismatch without editing files')
    args = parser.parse_args()
    version = (ROOT / 'VERSION').read_text().strip()
    number = r'(?:0|[1-9][0-9]*)'
    if not re.fullmatch(rf'{number}\.{number}\.{number}', version):
        parser.error('VERSION must contain a stable major.minor.patch version')
    manifest = ROOT / '.codex-plugin/plugin.json'
    data = json.loads(manifest.read_text())
    if data.get('version') != version:
        if args.check:
            parser.exit(1, f'{manifest.relative_to(ROOT)} version must match VERSION ({version})\n')
        data['version'] = version
        manifest.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
    print(f'Collection and host package versions: {version}')


if __name__ == '__main__':
    main()
