#!/usr/bin/env python3
"""Run isolated, paired skill evaluations with the Codex CLI (Python 3.11+).

Controller inputs, answer keys, logs, and fixtures stay outside the agent's
workspace. No user configuration is changed. See evals/README.md for limits.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import copy
import hashlib
import json
import math
import os
import random
import re
import shutil
import shlex
from functools import lru_cache
import signal
import subprocess
import sys
import tempfile
import time
if sys.version_info < (3, 11):
    raise SystemExit("Python 3.11+ is required; run python3.12 evals/run.py ...")
import tomllib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SUITE = ROOT / "evals/suites/private-company-research/suite.json"
ARMS = {"candidate", "baseline", "previous"}
SPLITS = {"dev", "regression", "holdout"}
CHECKS = {"tool_result_contains", "tool_before", "artifact_unchanged", "artifact_json", "artifact_csv", "no_write", "called", "not_called", "membership", "list_created", "max_calls", "tool_errors", "text_contains", "text_excludes", "semantic", "activation"}
try:
    from .artifacts_io import safe_relative, stage_attachments, capture_artifacts, MAX_BYTES
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from artifacts_io import safe_relative, stage_attachments, capture_artifacts, MAX_BYTES

SAFE_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$")
USAGE_KEYS = ("input_tokens", "output_tokens", "cached_input_tokens")


class EvalError(ValueError):
    """Invalid inputs or a setup failure, rather than a model outcome."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvalError(f"Cannot read JSON {path}: {exc}") from exc


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_hashes(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): file_hash(p) for p in sorted(root.rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts and p.name != ".DS_Store"}


def validate_check(check: dict[str, Any], case_id: str) -> None:
    specs = {
        "artifact_unchanged": ({"path", "from_turn"}, set()),
        "artifact_json": ({"path", "expected"}, set()),
        "artifact_csv": ({"path"}, {"columns", "key", "values", "rows"}),
        "tool_before": ({"tool", "before_tools"}, {"argument_contains"}),
        "tool_result_contains": ({"text"}, set()),
        "no_write": (set(), set()),
        "called": ({"tool"}, {"min", "max"}),
        "not_called": ({"tools"}, set()),
        "membership": ({"list_id", "entity_ids"}, {"mode"}),
        "list_created": ({"name", "entity_ids"}, set()),
        "max_calls": ({"limit"}, set()),
        "tool_errors": (set(), {"max", "allowed_codes"}),
        "text_contains": ({"phrases"}, {"all"}),
        "text_excludes": ({"phrases"}, set()),
        "semantic": ({"rubric"}, set()),
        "activation": ({"skill", "expected"}, set()),
    }
    required, optional = specs[check["kind"]]
    if check['kind'].startswith('artifact_'):
        try:
            safe_relative(check.get('path'))
        except ValueError as exc:
            raise EvalError(str(exc)) from exc
        if check['kind'] == 'artifact_unchanged' and (type(check.get('from_turn')) is not int or check['from_turn'] < 1 or check.get('turn', 0) <= check['from_turn']):
            raise EvalError('Unchanged artifact needs earlier from_turn and later turn')
        if check['kind'] == 'artifact_csv':
            if ('key' in check) != ('values' in check):
                raise EvalError('CSV key and values must appear together')
            for field in ('columns', 'values'):
                if field in check and (not isinstance(check[field], list) or any(not isinstance(v, str) for v in check[field]) or len(check[field]) != len(set(check[field]))):
                    raise EvalError('CSV columns/values must be unique strings')
            if 'rows' in check and (not isinstance(check['rows'], list) or any(not isinstance(r, dict) or any(type(v) not in (str, int, float) or (type(v) in (int, float) and not math.isfinite(v)) for v in r.values()) for r in check['rows'])):
                raise EvalError('CSV expected rows must contain strings or finite numbers')
    common = {"id", "kind", "severity", "turn", "arms"}
    if "arms" in check and (not isinstance(check["arms"], list) or not check["arms"] or any(a not in {"candidate", "baseline", "previous"} for a in check["arms"]) or len(set(check["arms"])) != len(check["arms"])):
        raise EvalError("Check arms must be a nonempty unique supported-arm list")
    missing = required - set(check)
    unknown = set(check) - common - required - optional
    if missing or unknown:
        raise EvalError(f"{case_id}/{check['id']}: missing fields {sorted(missing)}; unknown fields {sorted(unknown)}")
    for key in {"tool", "list_id", "name", "rubric", "skill", "text"} & set(check):
        if not isinstance(check[key], str) or not check[key].strip():
            raise EvalError(f"{case_id}/{check['id']}: {key} must be a nonempty string")
    for key in {"tools", "before_tools", "entity_ids", "phrases", "allowed_codes"} & set(check):
        values = check[key]
        if not isinstance(values, list) or not all(isinstance(v, str) and v for v in values):
            raise EvalError(f"{case_id}/{check['id']}: {key} must be an array of nonempty strings")
        if key in {"tools", "before_tools", "phrases"} and not values:
            raise EvalError(f"{case_id}/{check['id']}: {key} cannot be empty")
        if len(values) != len(set(values)):
            raise EvalError(f"{case_id}/{check['id']}: {key} contains duplicates")
    for key in {"min", "max", "limit"} & set(check):
        if type(check[key]) is not int or check[key] < 0:
            raise EvalError(f"{case_id}/{check['id']}: {key} must be a nonnegative integer")
    for key in ({"expected", "all"} if check["kind"] == "activation" else {"all"}) & set(check):
        if type(check[key]) is not bool:
            raise EvalError(f"{case_id}/{check['id']}: {key} must be boolean")
    if check['kind'] == 'tool_before':
        match = check.get('argument_contains', {})
        if not isinstance(match, dict) or any(not isinstance(k, str) or not k or not isinstance(v, str) or not v for k, v in match.items()):
            raise EvalError('argument_contains must contain nonempty string key/value pairs')
        if check['tool'] in check['before_tools']:
            raise EvalError('Ordered tool cannot also be a dependent tool')
    if check["kind"] == "called" and "max" in check and check["max"] < check.get("min", 1):
        raise EvalError(f"{case_id}/{check['id']}: max is less than min")
    if "mode" in check and check["mode"] not in {"exact", "includes"}:
        raise EvalError(f"{case_id}/{check['id']}: invalid membership mode")


def load_suite(path: Path) -> dict[str, Any]:
    suite = read_json(path)
    if not isinstance(suite, dict) or suite.get("schema_version") != 1:
        raise EvalError("Suite must be an object with schema_version: 1")
    if not isinstance(suite.get("id"), str) or not SAFE_ID.fullmatch(suite["id"]):
        raise EvalError("Suite id must be a safe, nonempty identifier")
    try:
        datetime.strptime(suite["as_of"], "%Y-%m-%d")
    except (KeyError, TypeError, ValueError) as exc:
        raise EvalError("Suite as_of must be YYYY-MM-DD") from exc
    if not isinstance(suite.get("cases"), list) or not suite["cases"]:
        raise EvalError("Suite must contain nonempty cases")
    if "context" in suite and not isinstance(suite["context"], str):
        raise EvalError("Suite context must be a string")
    seen: set[str] = set()
    families: dict[str, str] = {}
    for case in suite["cases"]:
        if not isinstance(case, dict):
            raise EvalError("Each case must be an object")
        cid = case.get("id", "")
        if not isinstance(cid, str) or not SAFE_ID.fullmatch(cid) or cid in seen:
            raise EvalError(f"Unsafe or duplicate case id: {cid!r}")
        seen.add(cid)
        if case.get("split") not in SPLITS:
            raise EvalError(f"{cid}: invalid split")
        if not all(isinstance(case.get(k), str) and case[k] for k in ("family", "workflow")):
            raise EvalError(f"{cid}: family and workflow must be nonempty strings")
        if case["family"] in families and families[case["family"]] != case["split"]:
            raise EvalError(f"Case family {case['family']} crosses dataset splits")
        families[case["family"]] = case["split"]
        if not isinstance(case.get("tags"), list) or not all(isinstance(t, str) for t in case["tags"]):
            raise EvalError(f"{cid}: tags must be strings")
        if not isinstance(case.get("fixture"), dict):
            raise EvalError(f"{cid}: fixture must be an object")
        if any(k in case["fixture"] for k in ("checks", "rubric", "reference_answer", "expected_answer")):
            raise EvalError(f"{cid}: answer keys do not belong in the replay fixture")
        for field in ('attachments', 'artifacts'):
            items = case.get(field, [])
            if not isinstance(items, list):
                raise EvalError(f'{cid}: {field} must be a list')
            paths = set()
            for item in items:
                allowed = {'path', 'content'} if field == 'attachments' else {'path', 'format'}
                if not isinstance(item, dict) or set(item) != allowed:
                    raise EvalError(f'{cid}: invalid {field} entry')
                try:
                    safe_relative(item['path'])
                except ValueError as exc:
                    raise EvalError(str(exc)) from exc
                if item['path'] in paths:
                    raise EvalError(f'{cid}: duplicate {field} path')
                paths.add(item['path'])
                if field == 'attachments' and (not isinstance(item['content'], str) or len(item['content'].encode()) > MAX_BYTES):
                    raise EvalError(f'{cid}: invalid attachment content')
                if field == 'artifacts' and item['format'] not in ('csv', 'json'):
                    raise EvalError(f'{cid}: invalid artifact format')
        turns = case.get("turns")
        if not isinstance(turns, list) or not turns:
            raise EvalError(f"{cid}: turns must be a nonempty array")
        if any(not isinstance(t, dict) or set(t) != {"user"} or not isinstance(t["user"], str) or not t["user"].strip() for t in turns):
            raise EvalError(f"{cid}: turns contain only actual, nonempty user messages")
        updates = case.get('fixture_updates', [])
        if not isinstance(updates, list):
            raise EvalError(f'{cid}: fixture_updates must be a list')
        update_turns = set()
        for update in updates:
            if not isinstance(update, dict) or set(update) - {'turn', 'as_of', 'fixture'} or not {'turn', 'fixture'} <= set(update):
                raise EvalError(f'{cid}: invalid fixture update')
            if type(update['turn']) is not int or not 2 <= update['turn'] <= len(turns) or update['turn'] in update_turns:
                raise EvalError(f'{cid}: invalid fixture update turn')
            update_turns.add(update['turn'])
            if not isinstance(update['fixture'], dict) or set(update['fixture']) - {'overrides', 'errors', 'empty_collections', 'base_data', 'page_size'}:
                raise EvalError(f'{cid}: unsupported fixture update')
            if 'as_of' in update:
                try:
                    datetime.strptime(update['as_of'], '%Y-%m-%d')
                except (ValueError, TypeError) as exc:
                    raise EvalError('Update clock must be YYYY-MM-DD') from exc
        if not isinstance(case.get("checks"), list) or not case["checks"]:
            raise EvalError(f"{cid}: checks must be nonempty")
        check_ids: set[str] = set()
        for check in case["checks"]:
            if not isinstance(check, dict) or check.get("kind") not in CHECKS:
                raise EvalError(f"{cid}: unsupported check kind")
            check_id = check.get("id", "")
            if not isinstance(check_id, str) or not SAFE_ID.fullmatch(check_id) or check_id in check_ids:
                raise EvalError(f"{cid}: unsafe or duplicate check id")
            check_ids.add(check_id)
            if check.get("severity") not in {"critical", "normal"}:
                raise EvalError(f"{cid}/{check_id}: invalid severity")
            if "turn" in check and (type(check["turn"]) is not int or not 1 <= check["turn"] <= len(turns)):
                raise EvalError(f"{cid}/{check_id}: turn is out of range")
            validate_check(check, cid)
            if check['kind'].startswith('artifact_') and check['path'] not in {a['path'] for a in case.get('artifacts', [])}:
                raise EvalError(f'{cid}: artifact check path is not captured')
    return suite


def select_cases(suite: dict[str, Any], case_ids: str | None, split: str) -> list[dict[str, Any]]:
    wanted = set(case_ids.split(",")) if case_ids else None
    splits = SPLITS if split == "all" else set(split.split(","))
    if not splits <= SPLITS:
        raise EvalError(f"Unknown split: {sorted(splits - SPLITS)}")
    known = {case["id"] for case in suite["cases"]}
    if wanted and not wanted <= known:
        raise EvalError(f"Unknown cases: {sorted(wanted - known)}")
    cases = [c for c in suite["cases"] if c["split"] in splits and (wanted is None or c["id"] in wanted)]
    if wanted and wanted != {c["id"] for c in cases}:
        raise EvalError("Some requested cases are excluded by --split; select the matching split explicitly")
    if not cases:
        raise EvalError("Case selection is empty")
    return cases


def make_plan(cases: list[dict[str, Any]], arms: list[str], repeats: int, seed: int) -> list[dict[str, Any]]:
    if repeats < 1 or not arms or len(arms) != len(set(arms)) or not set(arms) <= ARMS:
        raise EvalError("Use positive repeats and unique candidate, baseline, or previous arms")
    rng = random.Random(seed)
    blocks = [(c["id"], trial) for c in cases for trial in range(1, repeats + 1)]
    rng.shuffle(blocks)
    jobs = []
    for cid, trial in blocks:
        block_arms = arms.copy()
        rng.shuffle(block_arms)
        for arm in block_arms:
            job_id = f"{cid}__{arm}__r{trial:03d}"
            jobs.append({"job_id": job_id, "case_id": cid, "arm": arm, "trial": trial, "path": f"trials/{job_id}"})
    return jobs


def resolve_model(model: str | None, effort: str | None, config_path: Path | None = None) -> tuple[str, str, dict[str, Any]]:
    """Read only model choices; never copy auth or unrelated config to trials."""
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    path = config_path or codex_home / "config.toml"
    source: dict[str, Any] = {"model": "explicit" if model else "configured", "effort": "explicit" if effort else "configured"}
    config: dict[str, Any] = {}
    if (model is None or effort is None) and path.exists():
        try:
            config = tomllib.loads(path.read_text(encoding="utf-8"))
            source["config_path"] = str(path.resolve())
            source["config_sha256"] = file_hash(path)
            profile = config.get("profile")
            if profile:
                if not isinstance(profile, str) or not SAFE_ID.fullmatch(profile):
                    raise EvalError("Unsafe configured profile name")
                profile_path = path.parent / f"{profile}.config.toml"
                if not profile_path.exists():
                    raise EvalError(f"Configured profile does not exist: {profile_path}")
                config.update(tomllib.loads(profile_path.read_text(encoding="utf-8")))
                source["profile_sha256"] = file_hash(profile_path)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            raise EvalError(f"Cannot read configured model: {exc}") from exc
    model = model or config.get("model")
    effort = effort or config.get("model_reasoning_effort")
    if not isinstance(model, str) or not model.strip():
        raise EvalError("No configured model found; pass --model explicitly")
    if not isinstance(effort, str) or not effort.strip():
        raise EvalError("No configured reasoning effort found; pass --effort explicitly")
    if effort not in {"none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra"}:
        raise EvalError(f"Unknown reasoning effort: {effort}")
    return model, effort, source


def skill_metadata(path: Path) -> dict[str, str]:
    """Extract the two discovery fields without a third-party YAML dependency."""
    text = path.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if len(parts) != 3 or parts[0].strip():
        raise EvalError(f"Missing skill frontmatter: {path}")
    fields: dict[str, str] = {}
    lines = parts[1].splitlines()
    for i, line in enumerate(lines):
        match = re.match(r"^(name|description):\s*(.*)$", line)
        if not match:
            continue
        key, value = match.groups()
        if value in {">", ">-", "|", "|-"}:
            block = []
            for following in lines[i + 1:]:
                if following and not following[0].isspace():
                    break
                block.append(following.strip())
            value = " ".join(block).strip()
        elif value.startswith('"'):
            try:
                value = json.loads(value)
            except json.JSONDecodeError as exc:
                raise EvalError(f"Use a valid quoted scalar for {key}: {path}") from exc
        elif value.startswith("'") and value.endswith("'"):
            value = value[1:-1].replace("''", "'")
        fields[key] = value
    if not fields.get("name") or not fields.get("description"):
        raise EvalError(f"Skill needs name and description: {path}")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", fields["name"]):
        raise EvalError(f"Invalid skill name: {path}")
    if fields["name"] != path.parent.name:
        raise EvalError(f"Skill name must match directory: {path}")
    return fields


def validate_skill_tree(skills: Path) -> None:
    if skills.is_symlink() or any(p.is_symlink() for p in skills.rglob("*")):
        raise EvalError("Skill snapshots must not contain symlinks")
    if not skills.is_dir():
        raise EvalError(f"Skills directory does not exist: {skills}")


def copy_skill_tree(source: Path, destination: Path) -> None:
    validate_skill_tree(source)
    # Preserve links introduced after validation rather than reading their targets.
    shutil.copytree(source, destination, symlinks=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
    validate_skill_tree(destination)


@lru_cache(maxsize=1)
def python_runtime_paths() -> tuple[Path, ...]:
    """Controller's supported interpreter plus its actual non-system linked libraries."""
    roots = {Path(sys.base_prefix), Path(sys.base_prefix).resolve(), Path(sys.executable).resolve()}
    if sys.platform == 'darwin':
        import _hashlib
        # Resolve dependencies of the executable, framework and SHA implementation.
        pending = [Path(sys.executable).resolve(), Path(_hashlib.__file__).resolve()]
        inspected = set()
        while pending:
            binary = pending.pop()
            if binary in inspected:
                continue
            inspected.add(binary)
            output = subprocess.run(['/usr/bin/otool', '-L', str(binary)], capture_output=True, text=True, check=True).stdout
            for line in output.splitlines()[1:]:
                name = line.strip().split(' (', 1)[0]
                if not name.startswith('/') or name.startswith(('/usr/lib/', '/System/Library/')):
                    continue
                library = Path(name)
                if not library.exists():
                    raise EvalError('Missing Python runtime library: ' + name)
                roots.update((library, library.resolve()))
                pending.append(library.resolve())
    return tuple(sorted(roots))


def provision_python(workspace: Path) -> None:
    binary = workspace / '.eval-bin'
    binary.mkdir(exist_ok=True)
    # No site/user imports or inherited PYTHON* settings; local script imports work.
    wrapper = '#!/bin/sh\nexec ' + shlex.quote(str(Path(sys.executable).resolve())) + ' -E -s -S "$@"\n'
    for name in ('python', 'python3', f'python{sys.version_info.major}.{sys.version_info.minor}'):
        path = binary / name
        path.write_text(wrapper, encoding='utf-8')
        path.chmod(0o755)


def advance_clock(workspace: Path, as_of: str) -> str:
    """Replace the authoritative workspace clock and notify resumed sessions."""
    notice = f"Current controlled evaluation date: {as_of}. This supersedes all earlier evaluation dates for this turn."
    catalog = workspace / 'AGENTS.md'
    lines = catalog.read_text().splitlines()
    lines = [line for line in lines if not line.startswith(('Current date for this task:', 'Current controlled evaluation date:'))]
    catalog.write_text(notice + '\n' + '\n'.join(lines) + '\n')
    return notice


def prepare_workspace(workspace: Path, skills: Path | None, as_of: str, context: str = "") -> dict[str, str]:
    workspace.mkdir(parents=True, exist_ok=True)
    provision_python(workspace)
    common = f"Current controlled evaluation date: {as_of}. This is the initial clock; an explicit controlled-clock notice on a later turn supersedes it.\nUse the available tools when they are relevant to the user's request.\n"
    if context:
        common += "\n" + context.strip() + "\n"
    contents: dict[str, str] = {}
    if skills is not None:
        copy_skill_tree(skills, workspace / "skills")
        catalog = []
        for path in sorted((workspace / "skills").glob("*/SKILL.md")):
            metadata = skill_metadata(path)
            rel = str(path.relative_to(workspace))
            catalog.append(f"- {metadata['name']}: {metadata['description']} (file: {rel})")
            contents[rel] = path.read_text(encoding="utf-8")
        if not catalog:
            raise EvalError("No skills found for the candidate arm")
        common += "\nAvailable skills\nWhen a skill's description matches the request, read its SKILL.md and follow its instructions. Do not use irrelevant skills.\n" + "\n".join(catalog) + "\n"
    (workspace / "AGENTS.md").write_text(common, encoding="utf-8")
    return contents


def toml_value(value: Any) -> str:
    if isinstance(value, dict):
        return "{" + ",".join(json.dumps(k) + "=" + toml_value(v) for k, v in value.items()) + "}"
    if isinstance(value, list):
        return "[" + ",".join(toml_value(v) for v in value) + "]"
    if value is None:
        raise EvalError("TOML overrides cannot contain null")
    return json.dumps(value, ensure_ascii=False)


def native_catalog_names(prompt: list[dict[str, Any]]) -> list[str]:
    """Read only the native catalog section, never the injected task catalog."""
    names: set[str] = set()
    for message in prompt:
        for block in message.get('content', []):
            text = block.get('text', '')
            if '<skills_instructions>' not in text or '### Available skills\n' not in text:
                continue
            section = text.split('### Available skills\n', 1)[1].split('</skills_instructions>', 1)[0]
            for line in section.splitlines():
                if line.startswith('- '):
                    match = re.match(r'^- (.+?): ', line)
                    if not match:
                        raise EvalError('Cannot parse native skill catalog; isolation is unverified')
                    names.add(match.group(1))
    return sorted(names)


def render_catalog_probe(cli: str, workspace: Path, disabled: list[str], marker: str) -> list[dict[str, Any]]:
    # Metadata renderer only: no model turn, tool calls, auth copies or settings writes.
    command = [cli, 'debug', 'prompt-input', '--disable', 'plugins', '--disable', 'apps', '--disable', 'hooks',
               '--enable', 'skip_host_skill_discovery', '-c', 'project_doc_max_bytes=0',
               '-c', 'developer_instructions=' + toml_value(marker), '-c', 'mcp_servers={}',
               '-c', 'web_search="disabled"', '-c', 'agents.enabled=false',
               '-c', 'skills.config=' + toml_value([{'name': name, 'enabled': False} for name in disabled]),
               'Metadata-only evaluation catalog isolation check.']
    try:
        probe_env = dict(os.environ)
        probe_env["CODEX_HOME"] = str(workspace / ".probe-codex-home")
        result = subprocess.run(command, cwd=workspace, env=probe_env, capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise EvalError('Native prompt renderer failed; refusing an unverified evaluation')
        prompt = json.loads(result.stdout)
        if not isinstance(prompt, list):
            raise ValueError('expected prompt list')
        return prompt
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        raise EvalError('Cannot verify native catalog isolation') from exc


@lru_cache(maxsize=4)
def native_skill_isolation(cli: str) -> dict[str, Any]:
    """One metadata preflight per controller process, shared equally by all arms."""
    with tempfile.TemporaryDirectory(prefix='crunchbase-catalog-preflight-') as temp:
        workspace = Path(temp)
        canary = workspace / '.agents/skills/eval-native-discovery-canary'
        canary.mkdir(parents=True)
        (canary / 'SKILL.md').write_text('---\nname: eval-native-discovery-canary\ndescription: EVAL_NATIVE_CANARY_712903\n---\nMetadata probe only.\n')
        # Mirror only metadata, never user settings, credentials, or helper code.
        host_skills = Path(os.environ.get('CODEX_HOME', Path.home() / '.codex')) / 'skills'
        mirror = workspace / '.probe-codex-home/skills'
        mirror.mkdir(parents=True)
        if host_skills.is_dir():
            for entry in host_skills.rglob('SKILL.md'):
                target = mirror / entry.relative_to(host_skills)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(entry.read_bytes())
        marker = 'EVAL_EXPLICIT_CANDIDATE_CATALOG_712903'
        original = render_catalog_probe(cli, workspace, [], marker)
        names = native_catalog_names(original)
        if 'eval-native-discovery-canary' not in names:
            raise EvalError('Native discovery canary was not exposed; isolation probe is invalid')
        isolated = render_catalog_probe(cli, workspace, names, marker)
        rendered = json.dumps(isolated)
        if native_catalog_names(isolated) or 'EVAL_NATIVE_CANARY_712903' in rendered or marker not in rendered:
            raise EvalError('Native catalog isolation failed or explicit candidate catalog was lost')
        return {'method': 'native prompt-input canary + explicit disabled skill names',
                'disabled_names': names, 'native_catalog_after': [], 'candidate_injection_preserved': True,
                'probe_sha256': hashlib.sha256(rendered.encode()).hexdigest(),
                'limitation': 'Local CLI metadata renderer, not a captured remote inference request; discovery is frozen at controller startup.'}


def build_command(*, cli: str, workspace: Path, trial_dir: Path, fixture: Path, server: Path,
                  model: str, effort: str, turn: int, thread_id: str | None, ephemeral: bool,
                  protected_paths: list[Path]) -> list[str]:
    # The standalone MCP controller runs outside the agent shell sandbox. It is
    # the only registered MCP server, reads synthetic fixtures, and has no
    # upstream implementation. The agent's shell cannot read its inputs/state.
    filesystem: dict[str, Any] = {":minimal": "read", ":workspace_roots": {".": "write"}}
    for runtime_path in python_runtime_paths():
        if any(runtime_path == p or runtime_path.is_relative_to(p) or p.is_relative_to(runtime_path) for p in protected_paths):
            raise EvalError('Python runtime overlaps protected controller inputs')
        filesystem[str(runtime_path)] = 'read'
    for path in protected_paths:
        if workspace.is_relative_to(path) or path.is_relative_to(workspace):
            raise EvalError("Controller inputs/outputs must be outside the agent workspace")
        filesystem[str(path)] = "deny"
    overrides: dict[str, Any] = {
        "skills.config": [{"name": name, "enabled": False} for name in native_skill_isolation(cli)["disabled_names"]],
        "model_reasoning_effort": effort,
        "approval_policy": "never",
        "default_permissions": "skill-evaluation",
        "permissions.skill-evaluation.filesystem": filesystem,
        "permissions.skill-evaluation.network.enabled": False,
        "allow_login_shell": False,
        "agents.enabled": False,
        "shell_environment_policy.inherit": "none",
        "shell_environment_policy.set": {"PATH": str(workspace / ".eval-bin") + ":/usr/bin:/bin:/usr/sbin:/sbin"},
        "web_search": "disabled",
        "project_doc_max_bytes": 0,
        "developer_instructions": (workspace / "AGENTS.md").read_text(encoding="utf-8"),
        "notify": [],
        "suppress_unstable_features_warning": True,
        "mcp_servers": {"crunchbase_replay": {
            "command": sys.executable,
            "args": [str(server), "--fixture", str(fixture), "--log", str(trial_dir / "tools.jsonl"),
                     "--state", str(trial_dir / "state.json"), "--turn", str(turn)],
            "startup_timeout_sec": 20,
            "tool_timeout_sec": 30,
            "default_tools_approval_mode": "approve",
        }},
    }
    command = [cli, "exec"]
    if thread_id:
        command += ["resume"]
    command += ["--ignore-user-config", "--ignore-rules", "--json", "--skip-git-repo-check", "--strict-config",
                "--disable", "plugins", "--disable", "apps", "--disable", "hooks",
                "--enable", "skip_host_skill_discovery", "--model", model]
    if ephemeral:
        command.append("--ephemeral")
    if not thread_id:
        command += ["-C", str(workspace)]
    for key, value in overrides.items():
        command += ["-c", key + "=" + toml_value(value)]
    command += ["-o", str(trial_dir / "turns" / str(turn) / "final.txt")]
    if thread_id:
        command.append(thread_id)
    command.append("-")
    return command


def kill_process_group(proc: subprocess.Popen[str]) -> None:
    if os.name == "posix":
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            proc.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            pass
        # Kill surviving descendants even when the CLI exited after SIGTERM.
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.communicate()
    else:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True, timeout=15, check=False)
        proc.communicate()


def execute_command(command: list[str], prompt: str, directory: Path, workspace: Path, timeout: float) -> dict[str, Any]:
    directory.mkdir(parents=True, exist_ok=True)
    write_json(directory / "command.json", command)
    (directory / "prompt.txt").write_text(prompt, encoding="utf-8")
    started = time.monotonic()
    timed_out = False
    spawn_error = None
    returncode = None
    with (directory / "trace.jsonl").open("w", encoding="utf-8") as stdout, (directory / "stderr.txt").open("w", encoding="utf-8") as stderr:
        try:
            proc = subprocess.Popen(command, cwd=workspace, stdin=subprocess.PIPE, stdout=stdout, stderr=stderr,
                                    text=True, start_new_session=(os.name == "posix"))
            try:
                proc.communicate(prompt, timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                kill_process_group(proc)
            returncode = proc.returncode
        except (OSError, subprocess.SubprocessError) as exc:
            spawn_error = f"{type(exc).__name__}: {exc}"
            stderr.write(spawn_error + "\n")
    return {"duration_seconds": round(time.monotonic() - started, 6), "returncode": returncode,
            "timed_out": timed_out, "spawn_error": spawn_error}


def empty_builtin_inventory(item: dict[str, Any]) -> bool:
    """Allow only completed, empty built-in MCP inventories; no external data."""
    key = {"list_mcp_resources": "resources", "list_mcp_resource_templates": "resourceTemplates"}.get(item.get("tool"))
    if item.get("server") != "codex" or key is None or item.get("status") != "completed" or item.get("error"):
        return False
    arguments = item.get("arguments")
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            return False
    if arguments not in ({}, {"server": "crunchbase_replay"}):
        return False
    return normalize_tool_result(item.get("result")) == {key: []}


def parse_trace(directory: Path, execution: dict[str, Any]) -> dict[str, Any]:
    errors = []
    if execution.get("timed_out"):
        errors.append("timeout: child process group terminated")
    if execution.get("spawn_error"):
        errors.append(execution["spawn_error"])
    if execution.get("returncode") != 0:
        errors.append(f"Codex exited with {execution.get('returncode')}")
    events = []
    for number, line in enumerate((directory / "trace.jsonl").read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
            if not isinstance(event, dict) or not isinstance(event.get("type"), str):
                raise ValueError("event is not a typed object")
            events.append(event)
        except (json.JSONDecodeError, ValueError) as exc:
            errors.append(f"Malformed trace line {number}: {exc}")
    failed = [event for event in events if event.get("type") in {"turn.failed", "error"}]
    if failed:
        errors.append("Trace contains failed/error events: " + json.dumps(failed, ensure_ascii=False))
    completions = [event for event in events if event.get("type") == "turn.completed"]
    if len(completions) != 1:
        errors.append(f"Expected one completed turn, saw {len(completions)}")
    usage = {key: 0 for key in USAGE_KEYS}
    for event in completions:
        values = event.get("usage")
        if not isinstance(values, dict):
            errors.append("Completed turn has no usage accounting")
            continue
        for key in USAGE_KEYS:
            if key != "cached_input_tokens" and key not in values:
                errors.append(f"Missing usage field: {key}")
            value = values.get(key, 0)
            if type(value) is not int or value < 0:
                errors.append(f"Invalid usage field: {key}")
            else:
                usage[key] += value
    final_path = directory / "final.txt"
    final = final_path.read_text(encoding="utf-8").strip() if final_path.exists() else ""
    if not final:
        errors.append("No final assistant response was recorded")
    thread_ids = [event.get("thread_id") for event in events if event.get("type") == "thread.started"]
    thread_id = next((v for v in thread_ids if isinstance(v, str) and v), None)
    stderr = (directory / "stderr.txt").read_text(encoding="utf-8")
    if re.search(r"(?:mcp[^\n]*(?:startup\W+failed|failed to start)|failed to (?:initialize|start)[^\n]*mcp)", stderr, re.I):
        errors.append("Replay MCP server startup failed; see stderr")
    allowed_inventories = {event["item"].get("id"): event["item"] for event in events if event.get("type") == "item.completed" and empty_builtin_inventory(event.get("item", {}))}
    for event in events:
        item = event.get("item", {})
        allowed_inventory = (empty_builtin_inventory(item) or (item.get("id") in allowed_inventories and all(item.get(key) == allowed_inventories[item["id"]].get(key) for key in ("server", "tool", "arguments")) and item.get("status") == "in_progress" and item.get("result") is None and item.get("error") is None))
        if item.get("type") == "mcp_tool_call" and item.get("server") not in {None, "crunchbase_replay"} and not allowed_inventory:
            errors.append(f"Unexpected external MCP server: {item['server']}")
        if item.get("type") == "mcp_tool_call" and item.get("error"):
            error_text = json.dumps(item["error"], ensure_ascii=False)
            if re.search(r"requires approval|approval policy|not connected|connection (?:closed|refused)|transport error|server.*not found", error_text, re.I):
                errors.append("Replay tool infrastructure failure: " + error_text)
    return {"status": "infra_error" if errors else "completed", "error": "; ".join(errors) if errors else None,
            "final": final, "thread_id": thread_id, "usage": usage,
            "usage_complete": len(completions) == 1 and isinstance(completions[0].get("usage"), dict)
                and all(type(completions[0]["usage"].get(key)) is int for key in ("input_tokens", "output_tokens")),
            "events": events}


def normalize_tool_result(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    structured = value.get("structuredContent", value.get("structured_content"))
    if isinstance(structured, (dict, list)):
        return structured
    for block in value.get("content", []):
        if isinstance(block, dict) and block.get("type") == "text":
            try:
                parsed = json.loads(block.get("text", ""))
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(parsed, (dict, list)):
                return parsed
    return value


def extract_timeline(events: list[dict[str, Any]], turn: int) -> dict[str, Any]:
    """Preserve visible previews and attempted MCP calls, including client errors."""
    messages = []
    attempts: dict[str, dict[str, Any]] = {}
    for index, event in enumerate(events):
        item = event.get("item", {})
        if event.get("type") == "item.completed" and item.get("type") == "agent_message":
            messages.append({"type": "message", "text": item.get("text", ""), "phase": item.get("phase"), "event_index": index})
        if item.get("type") != "mcp_tool_call":
            continue
        identifier = str(item.get("id", f"event-{index}"))
        tool = str(item.get("tool", item.get("name", "")))
        if not tool:
            continue
        tool = tool.rsplit("__", 1)[-1]
        attempt = attempts.setdefault(identifier, {"turn": turn, "tool": tool, "arguments": {},
            "attempt_id": identifier, "event_index": index, "source": "codex_trace"})
        arguments = item.get("arguments", {})
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                arguments = {"_unparsed": arguments}
        if event.get('type') == 'item.completed':
            attempt['completed_event_index'] = index
        attempt.update({"arguments": arguments, "server": item.get("server"), "status": item.get("status", event.get("type"))})
        if "result" in item:
            attempt["result"] = normalize_tool_result(item["result"])
        if "error" in item and item["error"]:
            attempt["error"] = item["error"]
            attempt["result"] = {"error": {"code": "CLIENT_TOOL_ERROR", "message": item["error"]}}
    tool_attempts = list(attempts.values())
    timeline = messages + [{"type": "tool_call", **attempt} for attempt in tool_attempts]
    timeline.sort(key=lambda entry: entry["event_index"])
    return {"messages": messages, "timeline": timeline, "tool_attempts": tool_attempts}


def extract_skill_reads(events: list[dict[str, Any]], contents: dict[str, str], workspace: Path) -> list[str] | None:
    """Content-backed file-read evidence; return unknown for opaque read attempts."""
    reads: set[str] = set()
    uncertain = False
    read_command = re.compile(r"\b(cat|sed|head|tail|rg|grep|awk|read_text|readFile|open|Get-Content)\b")
    for event in events:
        if event.get("type") != "item.completed":
            continue
        item = event.get("item", {})
        if item.get("type") in {"agent_message", "reasoning", "mcp_tool_call", "todo_list"}:
            continue
        serialized = json.dumps(item, ensure_ascii=False)
        if item.get("type") != "command_execution":
            if "SKILL.md" in serialized and read_command.search(serialized):
                uncertain = True
            continue
        # A composite command may emit skill content before another operation fails.
        command = item.get("command", "")
        output = item.get("aggregated_output", "")
        if not isinstance(command, str) or not isinstance(output, str) or not read_command.search(command):
            continue
        cwd = str(item.get("cwd", item.get("working_directory", "")))
        is_skill_read = "SKILL.md" in command
        matched = False
        for rel, body in contents.items():
            directory = str(Path(rel).parent)
            named = rel in command or (directory in command + cwd and "SKILL.md" in command)
            # A basename-only command can still be proven by a unique frontmatter
            # name or heading present in the actual tool output.
            skill_name = Path(rel).parent.name
            identity = f"name: {skill_name}" in output
            evidence_lines = [line.strip() for line in body.splitlines() if len(line.strip()) >= 40]
            content_read = any(line in output for line in evidence_lines)
            if content_read and (named or identity):
                reads.add(rel)
                matched = True
        if is_skill_read and not matched:
            uncertain = True
    return None if uncertain else sorted(reads)


def validate_fixture_enums(data: dict[str, Any]) -> None:
    """Base records must agree with their exposed enum contracts; overrides may inject faults."""
    for collection, rows in data.get('entities', {}).items():
        contracts = data.get('contracts', {}).get(collection, {})
        for row in rows:
            for field, contract in contracts.items():
                value = row.get(field)
                if value is None or 'enum_values' not in contract:
                    continue
                values = value if isinstance(value, list) else [value]
                if any(v not in contract['enum_values'] for v in values):
                    identity = row.get('identifier', {}).get('uuid', '<unknown>')
                    raise EvalError(f'Fixture record {collection}/{identity} has {field}={value!r} outside its declared enum')


def materialize_fixture(case: dict[str, Any], suite_path: Path) -> dict[str, Any]:
    fixture = copy.deepcopy(case["fixture"])
    if "base_data" not in fixture:
        base = suite_path.parent / "base_data.json"
        if not base.exists():
            raise EvalError(f"No fixture base_data or sibling base_data.json for {case['id']}")
        fixture["base_data"] = read_json(base)
    validate_fixture_enums(fixture["base_data"])
    return fixture


def run_trial(job: dict[str, Any], case: dict[str, Any], run_dir: Path, manifest: dict[str, Any],
              suite_path: Path, candidate: Path, previous: Path | None, server: Path,
              cli: str, timeout: float) -> dict[str, Any]:
    trial_dir = run_dir / job["path"]
    trial_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {"schema_version": 1, **{k: job[k] for k in ("job_id", "case_id", "arm", "trial")},
        "model": manifest["model"], "reasoning_effort": manifest["reasoning_effort"], "status": "infra_error",
        "turns": [], "skill_reads": [], "tool_attempts": [], "usage": {key: 0 for key in USAGE_KEYS}, "manifest": {
            "run_manifest_sha256": file_hash(run_dir / "manifest.json"), "case_sha256": hashlib.sha256(json.dumps(case, sort_keys=True).encode()).hexdigest(),
            "suite_sha256": manifest["suite_sha256"], "candidate_skill_sha256": manifest["candidate_skill_sha256"],
            "previous_skill_sha256": manifest.get("previous_skill_sha256"), "fixture_sha256": None,
            "filesystem_isolation": "custom minimal-runtime + own workspace; controller paths explicitly denied; no fallback",
        }}
    started = time.monotonic()
    try:
        fixture_path = trial_dir / "fixture.json"
        frozen_fixture = run_dir / "inputs" / "fixtures" / (case["id"] + ".json")
        write_json(fixture_path, read_json(frozen_fixture) if frozen_fixture.exists() else materialize_fixture(case, suite_path))
        result["manifest"]["fixture_sha256"] = file_hash(fixture_path)
        # Seed state even when a clarification turn never starts the replay server.
        write_json(trial_dir / "state.json", {
            "lists": copy.deepcopy(read_json(fixture_path)["base_data"]["lists"]),
            "call_counts": {}, "successful_calls": {}, "created_count": 0,
        })
        (trial_dir / "tools.jsonl").touch()
        with tempfile.TemporaryDirectory(prefix="crunchbase-runtime-") as temporary:
            workspace = Path(temporary).resolve()
            skill_source = candidate if job["arm"] == "candidate" else previous if job["arm"] == "previous" else None
            contents = prepare_workspace(workspace, skill_source, manifest["as_of"], manifest.get("context", ""))
            result['manifest']['attachment_sha256'] = stage_attachments(workspace, case.get('attachments', []))
            result["manifest"]["runtime_workspace"] = str(workspace)
            result["manifest"]["catalog_sha256"] = file_hash(workspace / "AGENTS.md")
            result["manifest"]["runtime_files"] = tree_hashes(workspace)
            thread_id = None
            skill_reads = set()
            activation_known = True
            for turn, prompt in enumerate(case["turns"], 1):
                turn_dir = trial_dir / "turns" / str(turn)
                update = next((u for u in case.get('fixture_updates', []) if u['turn'] == turn), None)
                clock_notice = ""
                if update:
                    fixture = read_json(fixture_path)
                    fixture.update(copy.deepcopy(update['fixture']))
                    write_json(fixture_path, fixture)
                    if 'as_of' in update:
                        clock_notice = advance_clock(workspace, update['as_of'])
                turn_dir.mkdir(parents=True, exist_ok=True)
                write_json(turn_dir / 'fixture-before.json', read_json(fixture_path))
                command = build_command(cli=cli, workspace=workspace, trial_dir=trial_dir, fixture=fixture_path,
                    server=server, model=manifest["model"], effort=manifest["reasoning_effort"], turn=turn,
                    thread_id=thread_id, ephemeral=len(case["turns"]) == 1, protected_paths=[run_dir, ROOT])
                effective_prompt = (clock_notice + "\n\n" if clock_notice else "") + prompt["user"]
                execution = execute_command(command, effective_prompt, turn_dir, workspace, timeout)
                parsed = parse_trace(turn_dir, execution)
                events = parsed.pop("events")
                turn_reads = extract_skill_reads(events, contents, workspace)
                parsed.update(extract_timeline(events, turn))
                result["tool_attempts"].extend(parsed["tool_attempts"])
                if turn_reads is None:
                    activation_known = False
                else:
                    skill_reads.update(turn_reads)
                if len(case["turns"]) > 1 and turn == 1 and not parsed["thread_id"]:
                    parsed["status"] = "infra_error"
                    parsed["error"] = (parsed["error"] or "") + "; Missing thread id; cannot resume conversation"
                observed_thread = parsed.get("thread_id")
                if thread_id and observed_thread and observed_thread != thread_id:
                    parsed["status"] = "infra_error"
                    parsed["error"] = "Resume unexpectedly created a different thread"
                thread_id = thread_id or observed_thread
                parsed["thread_id"] = thread_id
                parsed.update({"turn": turn, "duration_seconds": execution["duration_seconds"], "skill_reads": turn_reads,
                               "returncode": execution["returncode"], "timed_out": execution["timed_out"]})
                parsed["state_after"] = read_json(trial_dir / "state.json")
                parsed['artifacts'] = capture_artifacts(workspace, case.get('artifacts', []), turn_dir / 'artifacts')
                parsed['fixture_sha256'] = file_hash(turn_dir / 'fixture-before.json')
                result["turns"].append(parsed)
                for key in USAGE_KEYS:
                    result["usage"][key] += parsed["usage"][key]
                if parsed["status"] != "completed":
                    result["error"] = parsed["error"]
                    break
            result["skill_reads"] = sorted(skill_reads) if activation_known else None
            result["activation_observability"] = "complete" if activation_known else "unknown"
            if len(result["turns"]) == len(case["turns"]) and all(t["status"] == "completed" for t in result["turns"]):
                result["status"] = "completed"
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    result["duration_seconds"] = round(time.monotonic() - started, 6)
    result["usage_complete"] = bool(result["turns"]) and all(turn.get("usage_complete", False) for turn in result["turns"])
    result["cost_proxy"] = {"unit": "tokens_not_currency", "complete": result["usage_complete"],
        "note": "Observed token counts only; when incomplete, missing terminal usage is unknown, not zero consumption.", **result["usage"],
        "uncached_input_tokens": max(0, result["usage"]["input_tokens"] - result["usage"]["cached_input_tokens"])}
    if not (trial_dir / "state.json").exists():
        write_json(trial_dir / "state.json", {"lists": {}})
    write_json(trial_dir / "trial.json", result)
    return result


def validate_output_location(output: Path, candidate: Path, previous: Path | None) -> None:
    output = output.resolve()
    for source in (candidate, previous):
        if source is None:
            continue
        source = source.resolve()
        if output == source or source in output.parents or output in source.parents:
            raise EvalError("Evaluation output must be disjoint from candidate and previous skill directories")


def create_manifest(args: argparse.Namespace, suite: dict[str, Any], suite_path: Path,
                    jobs: list[dict[str, Any]], model: str, effort: str, source: dict[str, Any], run_dir: Path) -> dict[str, Any]:
    validate_output_location(run_dir, args.skills, args.previous_skills)
    validate_skill_tree(args.skills)
    if args.previous_skills is not None:
        validate_skill_tree(args.previous_skills)
    write_json(run_dir / "suite.json", suite)
    inputs = run_dir / "inputs"
    inputs.mkdir()
    selected_ids = {job["case_id"] for job in jobs}
    for case in suite["cases"]:
        if case["id"] in selected_ids:
            write_json(inputs / "fixtures" / (case["id"] + ".json"), materialize_fixture(case, suite_path))
    shutil.copy2(ROOT / "evals/replay_server.py", inputs / "replay_server.py")
    candidate = args.skills.resolve()
    previous = args.previous_skills.resolve() if args.previous_skills else None
    copy_skill_tree(candidate, inputs / "candidate-skills")
    if previous:
        copy_skill_tree(previous, inputs / "previous-skills")
    cli_version = subprocess.run([args.codex, "--version"], capture_output=True, text=True, timeout=30, check=True).stdout.strip()
    harness = {str(p.relative_to(ROOT)): file_hash(p) for p in sorted((ROOT / "evals").glob("*.py"))}
    manifest = {"schema_version": 1, "run_id": run_dir.name, "created_at": utc_now(), "suite_id": suite["id"],
        "as_of": suite["as_of"], "context": suite.get("context", ""),
        "full_suite": args.case is None and {j["case_id"] for j in jobs} == {c["id"] for c in suite["cases"]},
        "suite_path": "suite.json", "suite_sha256": file_hash(run_dir / "suite.json"),
        "suite_source_sha256": file_hash(suite_path), "candidate_skill_sha256": tree_hashes(inputs / "candidate-skills"),
        "previous_skill_sha256": tree_hashes(inputs / "previous-skills") if previous else None,
        "replay_server_sha256": file_hash(inputs / "replay_server.py"),
        "effective_fixture_sha256": tree_hashes(inputs / "fixtures"),
        "harness_sha256": harness, "fixture_base_sha256": file_hash(suite_path.parent / "base_data.json") if (suite_path.parent / "base_data.json").exists() else None,
        "codex_version": cli_version, "python_version": sys.version,
        "agent_python": {"executable": str(Path(sys.executable).resolve()), "sha256": file_hash(Path(sys.executable).resolve()), "read_paths": [str(p) for p in python_runtime_paths()], "flags": ["-E", "-s", "-S"], "arms": "identical"}, "model": model, "reasoning_effort": effort,
        "model_resolution": source, "seed": args.seed, "repeats": args.repeats, "arms": args.arms.split(","),
        "budgets": {"timeout_seconds_per_turn": args.timeout, "jobs": args.jobs}, "jobs": jobs,
        "isolation": {"user_config": "ignored; host project documents disabled; generated catalog injected explicitly", "plugins": "disabled", "apps": "disabled", "hooks": "disabled",
            "web": "disabled", "shell_network": "disabled", "host_skills": "explicit native-name disables verified by metadata canary",
            "native_catalog_preflight": native_skill_isolation(args.codex),
            "agent_filesystem": "minimal OS runtime plus per-trial workspace; deny controller repository and run artifacts",
            "mcp": "only synthetic stdio replay server; no live backend", "routing": "all skill descriptions available; no expected skill in prompt",
            "multi_turn": "actual persisted Codex resume, state/log retained; single turns ephemeral",
            "limits": "Host-managed policy may constrain execution; any setup/trace failure stays an infrastructure error. Token totals are cost proxies, not currency. Runtime activation is an explicit catalog simulation, not a plugin discovery test."}}
    write_json(run_dir / "manifest.json", manifest)
    return manifest


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=("validate", "plan", "run"))
    p.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    p.add_argument("--case", help="Comma-separated case IDs")
    p.add_argument("--split", default="dev,regression", help="dev,regression (default), holdout, or all")
    p.add_argument("--repeats", type=int, default=3)
    p.add_argument("--arms", default="candidate,baseline")
    p.add_argument("--model")
    p.add_argument("--effort")
    p.add_argument("--model-config", type=Path, help="Read model/effort only from this config file")
    p.add_argument("--seed", type=int, default=20260930)
    p.add_argument("--jobs", type=int, default=2)
    p.add_argument("--timeout", type=float, default=360)
    p.add_argument("--output", type=Path, default=ROOT / "evals/artifacts", help="Parent directory for a unique run folder; outside agent workspaces")
    p.add_argument("--skills", type=Path, default=ROOT / "skills")
    p.add_argument("--previous-skills", type=Path)
    p.add_argument("--codex", default="codex")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        suite_path = args.suite.resolve()
        suite = load_suite(suite_path)
        cases = select_cases(suite, args.case, args.split)
        arms = args.arms.split(",")
        jobs = make_plan(cases, arms, args.repeats, args.seed)
        if args.jobs < 1 or args.timeout <= 0:
            raise EvalError("--jobs and --timeout must be positive")
        if "previous" in arms and not args.previous_skills:
            raise EvalError("The previous arm requires --previous-skills")
        for skills in [args.skills] + ([args.previous_skills] if args.previous_skills else []):
            if not skills.is_dir() or not list(skills.glob("*/SKILL.md")):
                raise EvalError(f"No skill collection at {skills}")
            for path in skills.glob("*/SKILL.md"):
                skill_metadata(path)
        for case in cases:
            materialize_fixture(case, suite_path)
        if args.command == "validate":
            print(json.dumps({"valid": True, "suite": suite["id"], "cases": len(suite["cases"]), "selected_cases": len(cases)}, indent=2))
            return 0
        model, effort, source = resolve_model(args.model, args.effort, args.model_config)
        plan = {"schema_version": 1, "suite": suite["id"], "model": model, "reasoning_effort": effort,
                "seed": args.seed, "repeats": args.repeats, "jobs": jobs, "trials": len(jobs),
                "maximum_turns": sum(len(next(c for c in cases if c["id"] == j["case_id"])["turns"]) for j in jobs)}
        if args.command == "plan":
            print(json.dumps(plan, indent=2))
            return 0
        server = ROOT / "evals/replay_server.py"
        if not server.exists():
            raise EvalError(f"Missing replay server: {server}")
        validate_output_location(args.output, args.skills, args.previous_skills)
        run_dir = args.output.resolve() / ("run-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8])
        run_dir.mkdir(parents=True, exist_ok=False)
        manifest = create_manifest(args, suite, suite_path, jobs, model, effort, source, run_dir)
        write_json(run_dir / "run.json", {"status": "running", "planned_jobs": jobs, "completed_jobs": []})
        print(json.dumps({"run_dir": str(run_dir), "trials": len(jobs)}), flush=True)
        by_id = {case["id"]: case for case in cases}
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
            futures = {pool.submit(run_trial, job, by_id[job["case_id"]], run_dir, manifest, suite_path,
                run_dir / "inputs/candidate-skills", run_dir / "inputs/previous-skills" if args.previous_skills else None,
                run_dir / "inputs/replay_server.py", args.codex, args.timeout): job for job in jobs}
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                results.append({"job_id": result["job_id"], "status": result["status"]})
                write_json(run_dir / "run.json", {"status": "running", "planned_jobs": jobs, "completed_jobs": results})
                print(json.dumps(results[-1]), flush=True)
        success = len(results) == len(jobs) and all(r["status"] == "completed" for r in results)
        write_json(run_dir / "run.json", {"status": "completed" if success else "infra_error", "planned_jobs": jobs,
                                        "completed_jobs": results, "finished_at": utc_now()})
        return 0 if success else 2
    except (EvalError, OSError, subprocess.SubprocessError) as exc:
        print(f"Evaluation setup error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
