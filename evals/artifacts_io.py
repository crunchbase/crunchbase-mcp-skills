"""Bounded, allowlisted input/output evidence for offline agent evaluations."""
from __future__ import annotations
import csv
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath

MAX_BYTES = 2_000_000


def safe_relative(value):
    if not isinstance(value, str) or not value or '\\' in value:
        raise ValueError('Artifact path must be a nonempty POSIX relative path')
    path = PurePosixPath(value)
    if path.is_absolute() or any(p in ('..', '.') for p in value.split('/')) or '' in value.split('/'):
        raise ValueError('Artifact path must not escape the workspace')
    if path.parts[0] in ('skills', '.git', '.codex', '.eval-bin') or value == 'AGENTS.md':
        raise ValueError('Attachments/artifacts cannot replace runtime instructions or skills')
    return value


def confined(root, relative):
    safe_relative(relative)
    target = root / relative
    # Reject symlinks even when they currently resolve inside the root.
    for parent in (target, *target.parents):
        if parent == root:
            break
        if parent.is_symlink():
            raise ValueError('Symlinks cannot be captured as evidence')
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError('Artifact escapes workspace')
    return target


def stage_attachments(workspace, attachments):
    hashes = {}
    for item in attachments:
        target = confined(workspace, item['path'])
        data = item['content'].encode('utf-8')
        if len(data) > MAX_BYTES:
            raise ValueError('Attachment exceeds evidence byte limit')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        hashes[item['path']] = hashlib.sha256(data).hexdigest()
    return hashes


def capture_artifacts(workspace, specs, destination):
    """Missing/invalid outputs remain explicit evidence, not omitted records."""
    records = []
    for spec in specs:
        item = {'path': spec['path'], 'format': spec['format'], 'status': 'missing'}
        try:
            target = confined(workspace, spec['path'])
            if target.exists():
                if not target.is_file() or target.stat().st_size > MAX_BYTES:
                    raise ValueError('Output is not a bounded regular file')
                data = target.read_bytes()
                item.update(status='captured', sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))
                text = data.decode('utf-8-sig')
                if spec['format'] == 'json':
                    item['content'] = json.loads(text, parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))
                else:
                    reader = csv.DictReader(io.StringIO(text))
                    if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
                        raise ValueError('CSV requires unique nonempty headers')
                    item['columns'] = reader.fieldnames
                    item['content'] = list(reader)
                    if any(None in row or any(v is None for v in row.values()) for row in item['content']):
                        raise ValueError('CSV row width differs from headers')
                saved = confined(destination, spec['path'])
                saved.parent.mkdir(parents=True, exist_ok=True)
                saved.write_bytes(data)
        except (OSError, ValueError, UnicodeError) as exc:
            item.update(status='invalid', error=str(exc))
        records.append(item)
    return records


def subset(expected, actual):
    """Typed structural subset: arrays are ordered/exact length, maps may add keys."""
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(k in actual and subset(v, actual[k]) for k, v in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(expected) == len(actual) and all(subset(a, b) for a, b in zip(expected, actual))
    return type(expected) is type(actual) and expected == actual


def csv_row_matches(expected, actual):
    for key, value in expected.items():
        if key not in actual:
            return False
        if type(value) in (int, float):
            try:
                observed = float(actual[key])
            except (TypeError, ValueError):
                return False
            if not math.isfinite(observed) or observed != value:
                return False
        elif value != actual[key]:
            return False
    return True


def csv_rows_match(expected, actual):
    """One-to-one row matching; broad subset rows cannot consume the same row twice."""
    if len(expected) != len(actual):
        return False
    owners = {}
    def assign(index, visited):
        for candidate, row in enumerate(actual):
            if candidate in visited or not csv_row_matches(expected[index], row):
                continue
            visited.add(candidate)
            if candidate not in owners or assign(owners[candidate], visited):
                owners[candidate] = index
                return True
        return False
    return all(assign(index, set()) for index in range(len(expected)))


def check_artifact(check, records):
    found = [a for a in records if a.get('path') == check['path']]
    if len(found) != 1 or found[0].get('status') != 'captured':
        return False, 'Required artifact missing or invalid: ' + check['path']
    artifact = found[0]
    content = artifact.get('content')
    if check['kind'] == 'artifact_json':
        passed = artifact.get('format') == 'json' and subset(check['expected'], content)
    else:
        passed = artifact.get('format') == 'csv' and isinstance(content, list)
        passed = passed and set(check.get('columns', [])) <= set(artifact.get('columns', []))
        if passed and 'key' in check:
            ids = [row.get(check['key']) for row in content]
            passed = len(ids) == len(set(ids)) and set(ids) == set(check['values'])
        if passed and 'rows' in check:
            passed = csv_rows_match(check['rows'], content)
    return passed, ('Matched' if passed else 'Mismatched') + ' typed artifact contract: ' + check['path']
