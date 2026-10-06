#!/usr/bin/env python3
"""Build reproducible individual skill archives from Git-tracked package files."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='output directory (default: dist/<version>)')
    args = parser.parse_args()
    version = (ROOT / 'VERSION').read_text().strip()
    if not re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', version):
        parser.error('VERSION must contain a stable major.minor.patch version')
    if json.loads((ROOT / '.codex-plugin/plugin.json').read_text())['version'] != version:
        parser.error('Run scripts/sync_version.py to synchronize package versions')
    output = args.output or ROOT / 'dist' / version
    if output.exists() and any(output.iterdir()):
        parser.error("Output directory must be empty; choose a fresh --output directory")
    output.mkdir(parents=True, exist_ok=True)
    tracked = subprocess.check_output(
        ['git', 'ls-files', '-z', '--', 'skills/'], cwd=ROOT
    ).decode().split('\0')
    packages = {}
    for name in filter(None, tracked):
        path = Path(name)
        if len(path.parts) < 3:
            continue
        source = ROOT / path
        if source.is_symlink() or not source.is_file():
            parser.error(f'Package source must be a regular file: {name}')
        packages.setdefault(path.parts[1], []).append(path)
    if not packages:
        parser.error('No Git-tracked skill packages found')
    checksums = []
    for skill, paths in sorted(packages.items()):
        required = {Path('skills') / skill / name for name in ('SKILL.md', 'LICENSE', 'NOTICE')}
        if not required.issubset(paths):
            parser.error(f'{skill} is missing SKILL.md or license notices')
        archive = output / f'{skill}.zip'
        contents = {str(p.relative_to('skills')): (ROOT / p).read_bytes() for p in paths}
        contents[f'{skill}/VERSION'] = (version + '\n').encode()
        with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as z:
            for name, data in sorted(contents.items()):
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, data)
        with zipfile.ZipFile(archive) as z:
            if z.testzip() is not None or set(z.namelist()) != set(contents):
                raise RuntimeError(f'Archive validation failed: {archive}')
            for name, data in contents.items():
                if z.read(name) != data:
                    raise RuntimeError(f'Archive content mismatch: {name}')
        payload = archive.read_bytes()
        alternate = archive.with_suffix('.skill')
        alternate.write_bytes(payload)
        for asset in (archive, alternate):
            checksums.append(f'{hashlib.sha256(payload).hexdigest()}  {asset.name}\n')
        print(f'{skill}: .zip + .skill ({len(contents)} files each)')
    (output / 'SHA256SUMS').write_text(''.join(sorted(checksums)))
    print(f'Release {version}: {len(packages) * 2} archives in {output.resolve()}')


if __name__ == '__main__':
    main()
