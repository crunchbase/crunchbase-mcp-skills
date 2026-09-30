#!/usr/bin/env python3
"""Outcome and trace checks. Unknown judgments never silently become passes."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

WRITE_TOOLS = {"cb_list_create", "cb_list_add_entities", "cb_list_delete", "cb_list_remove_entities", "cb_list_update"}
KINDS = {"no_write", "called", "not_called", "membership", "list_created", "max_calls", "tool_errors", "text_contains", "text_excludes", "semantic", "activation"}


def canonical_tool(value):
    value = str(value)
    index = value.rfind("cb_")
    return value[index:] if index >= 0 else value


def review_key(trial, check):
    return f"{trial['case_id']}/{trial['arm']}/{trial['trial']}/{check['id']}"


def evidence_digest(case, trial, events, state):
    # Exclude machine-specific paths and evaluator labels from blinded evidence.
    payload = {"case_contract": case, "turns": [{k: t[k] for k in ("turn", "final", "messages", "timeline") if k in t} for t in trial.get("turns", [])], "events": events, "state": state}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def grade_case(case, trial, events, state, review=None):
    review = review or {}
    checks = []
    digest = evidence_digest(case, trial, events, state)
    for check in case["checks"]:
        kind = check["kind"]
        selected = [e for e in events if "turn" not in check or e.get("turn") == check["turn"]]
        finals = "\n".join(t.get("final", "") for t in trial.get("turns", []) if "turn" not in check or t.get("turn") == check["turn"])
        names = [canonical_tool(e.get("tool")) for e in selected]
        status, detail = "failed", ""
        passed = False
        if kind == "no_write":
            writes = [n for n in names if n in WRITE_TOOLS]
            passed, detail = not writes, f"Attempted mutations: {writes}"
        elif kind == "called":
            count = names.count(canonical_tool(check["tool"]))
            passed = check.get("min", 1) <= count <= check.get("max", float("inf"))
            detail = f"{check['tool']}: {count} calls"
        elif kind == "not_called":
            forbidden = set(map(canonical_tool, check["tools"]))
            found = sorted(set(names) & forbidden)
            passed, detail = not found, f"Forbidden calls: {found}"
        elif kind in {"membership", "list_created"}:
            selected_state = state
            if "turn" in check:
                snapshots = [e["state_after"] for e in selected if "state_after" in e]
                selected_state = snapshots[-1] if snapshots else {}
            lists = selected_state.get("lists", {})
            if kind == "membership":
                candidates = [lists[check["list_id"]]] if check["list_id"] in lists else []
            else:
                candidates = [v for v in lists.values() if v.get("name") == check["name"]]
            actual = set(candidates[0].get("entity_ids", [])) if len(candidates) == 1 else set()
            expected = set(check["entity_ids"])
            passed = len(candidates) == 1 and (expected <= actual if check.get("mode") == "includes" else actual == expected)
            if kind == "list_created":
                passed = passed and any(canonical_tool(e.get("tool")) == "cb_list_create" and e.get("arguments", {}).get("name") == check["name"] and not e.get("result", {}).get("error") for e in selected)
            detail = f"Matching lists: {len(candidates)}; expected {sorted(expected)}; observed {sorted(actual)}"
        elif kind == "max_calls":
            passed, detail = len(selected) <= check["limit"], f"{len(selected)} calls; cap {check['limit']}"
        elif kind == "tool_errors":
            allowed = set(check.get("allowed_codes", []))
            errors = []
            for e in selected:
                result = e.get("result", {})
                error = result.get("error") if isinstance(result, dict) else None
                if error and (not isinstance(error, dict) or error.get("code") not in allowed):
                    errors.append(error)
            passed = len(errors) <= check.get("max", 0)
            detail = f"Unexpected tool errors: {errors}"
        elif kind in {"text_contains", "text_excludes"}:
            present = [s for s in check["phrases"] if s.casefold() in finals.casefold()]
            if kind == "text_excludes":
                passed = not present
            else:
                passed = len(present) == len(check["phrases"]) if check.get("all", True) else bool(present)
            detail = f"Matched phrases: {present}"
        elif kind == "activation":
            if trial["arm"] == "baseline":
                status, detail = "skipped", "No-skill baseline; activation is not a common outcome metric."
            else:
                reads = trial.get("skill_reads")
                if reads is None:
                    status, detail = "needs_review", "No reliable skill-access instrumentation."
                else:
                    activated = any(check["skill"] in p for p in reads)
                    passed, detail = activated == check["expected"], f"Observed skill reads: {reads}"
        elif kind == "semantic":
            item = review.get(review_key(trial, check))
            if not item:
                status, detail = "needs_review", check["rubric"]
            elif item.get("evidence_digest") != digest:
                status, detail = "needs_review", "Review does not match this frozen transcript and state."
            elif item.get("source") != "human" or not item.get("reviewer") or not item.get("evidence") or type(item.get("pass")) is not bool:
                status, detail = "needs_review", "Requires an identified human reviewer, binary judgment, and evidence; model advice is provisional."
            else:
                passed, detail = item["pass"], item["evidence"]
        else:
            detail = f"Unknown check kind: {kind}"
        if status == "failed" and passed:
            status = "passed"
        scored = {"id": check["id"], "kind": kind, "severity": check.get("severity", "normal"), "status": status, "detail": detail}
        if kind == "activation":
            scored["expected"] = check["expected"]
            scored["observed"] = (check["expected"] if status == "passed" else not check["expected"]) if status in {"passed", "failed"} else None
        checks.append(scored)
    outcome_checks = [c for c in checks if c["kind"] != "activation"]
    def aggregate(items):
        if trial.get("status") != "completed":
            return "infra_error"
        if not items:
            return "needs_review"
        if any(c["status"] == "failed" for c in items):
            return "failed"
        if any(c["status"] == "needs_review" for c in items):
            return "needs_review"
        return "passed"
    tool_errors = []
    for event in events:
        result = event.get("result", {})
        error = result.get("error") if isinstance(result, dict) else None
        if error:
            tool_errors.append({"turn": event.get("turn"), "tool": canonical_tool(event.get("tool")), "code": error.get("code", "UNKNOWN") if isinstance(error, dict) else "UNKNOWN"})
    return {"case_id": case["id"], "family": case["family"], "split": case["split"], "workflow": case["workflow"], "arm": trial["arm"], "trial": trial["trial"], "status": aggregate(checks), "outcome_status": aggregate(outcome_checks), "checks": checks, "duration_seconds": trial.get("duration_seconds"), "usage": trial.get("usage", {}), "evidence_digest": digest, "error": trial.get("error"), "observed_tool_errors": tool_errors}


def read_jsonl(path):
    if not path.exists():
        return []
    entries = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if any(not isinstance(entry, dict) or not isinstance(entry.get("tool"), str) or not isinstance(entry.get("arguments"), dict) for entry in entries):
        raise ValueError("Invalid replay tool-log entry")
    return entries


def merge_attempts(events, attempts):
    """Count CLI attempts that never reached the server, without doubling calls."""
    from collections import Counter
    def normalize(event):
        event = dict(event)
        result = event.get("result") or {}
        if isinstance(result, dict) and isinstance(result.get("structuredContent"), dict):
            result = result["structuredContent"]
        elif isinstance(result, dict) and isinstance(result.get("structured_content"), dict):
            result = result["structured_content"]
        elif isinstance(result, dict) and isinstance(result.get("content"), list):
            for block in result["content"]:
                if isinstance(block, dict) and block.get("type") == "text":
                    try:
                        parsed = json.loads(block.get("text", ""))
                    except (ValueError, TypeError):
                        continue
                    if isinstance(parsed, dict):
                        result = parsed
                        break
        if not (isinstance(result, dict) and result.get("error")) and (event.get("error") or event.get("status") in {"failed", "cancelled"}):
            result = {"error": {"code": "CLIENT_TOOL_ERROR", "message": str(event.get("error") or event["status"])}}
        event["result"] = result
        return event
    def key(event):
        result = event.get("result", {})
        error = result.get("error") if isinstance(result, dict) else None
        error_code = error.get("code") if isinstance(error, dict) else str(error) if error else None
        return (event.get("turn"), canonical_tool(event.get("tool")), json.dumps(event.get("arguments", {}), sort_keys=True), error_code)
    remaining = Counter(key(event) for event in events)
    merged = list(events)
    for raw_attempt in attempts:
        attempt = normalize(raw_attempt)
        identity = key(attempt)
        if remaining[identity]:
            remaining[identity] -= 1
        else:
            merged.append({**attempt, "source": "client_attempt", "result": attempt.get("result") or {"error": {"code": "CLIENT_TOOL_ERROR", "message": "Attempt did not reach the fixture server"}}})
    return merged


def load_run(run):
    """Load the frozen suite and every planned trial; missing jobs remain visible."""
    manifest = json.loads((run / "manifest.json").read_text())
    suite_path = run / "suite.json"
    suite = json.loads(suite_path.read_text())
    expected = manifest.get("suite_sha256")
    if expected and hashlib.sha256(suite_path.read_bytes()).hexdigest() != expected:
        raise ValueError("Frozen suite hash mismatch")
    cases = {c["id"]: c for c in suite["cases"]}
    entries = []
    jobs = manifest.get("jobs", [])
    if not jobs:
        raise ValueError("Run has no planned jobs; refusing an empty or unplanned report")
    # Do not trust a flag alone: selected cases must cover the frozen full corpus.
    manifest["full_suite"] = bool(manifest.get("full_suite")) and {j["case_id"] for j in jobs if j["arm"] == "candidate"} == set(cases)
    seen = set()
    for job in jobs:
        key = (job["case_id"], job["arm"], job["trial"])
        if key in seen:
            raise ValueError(f"Duplicate planned trial: {key}")
        seen.add(key)
        directory = (run / job["path"]).resolve()
        if not directory.is_relative_to(run.resolve()):
            raise ValueError("Trial path escapes run directory")
        fallback = {"schema_version": 1, "case_id": job["case_id"], "arm": job["arm"], "trial": job["trial"], "status": "infra_error", "error": "Missing or invalid planned trial artifacts", "turns": [], "usage": {}}
        try:
            trial = json.loads((directory / "trial.json").read_text())
            if (trial["case_id"], trial["arm"], trial["trial"]) != key:
                raise ValueError("Trial identity does not match plan")
            case = cases[job["case_id"]]
            if trial.get("status") == "completed" and len(trial.get("turns", [])) != len(case["turns"]):
                raise ValueError("Completed trial has missing turns")
            if not (directory / "tools.jsonl").exists() or not (directory / "state.json").exists():
                raise ValueError("Missing replay evidence")
            events = read_jsonl(directory / "tools.jsonl")
            events = merge_attempts(events, trial.get("tool_attempts", []))
            state = json.loads((directory / "state.json").read_text())
        except (OSError, ValueError, KeyError) as exc:
            trial, events, state = fallback, [], {}
            trial["error"] = str(exc)
        entries.append((cases[job["case_id"]], trial, events, state))
    return manifest, entries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--reviews", type=Path)
    args = parser.parse_args()
    manifest, entries = load_run(args.run)
    reviews = json.loads(args.reviews.read_text()) if args.reviews else {}
    scores = [grade_case(*entry, review=reviews) for entry in entries]
    (args.run / "scores.json").write_text(json.dumps(scores, indent=2) + "\n")
    try:
        from .report import build_report
    except ImportError:
        from report import build_report
    report, summary = build_report(scores, manifest)
    (args.run / "report.md").write_text(report)
    (args.run / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(report)
    return 0 if summary["release_gate"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
