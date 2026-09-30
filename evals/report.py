"""Paired case-level estimates; pending reviews and failures retain denominators."""
from __future__ import annotations

import collections
import math
import random
import statistics


def paired_estimate(scores, baseline="baseline", samples=5000, seed=19):
    arms = {"candidate": {}, baseline: {}}
    for score in scores:
        if score["arm"] in arms:
            arms[score["arm"]].setdefault(score["case_id"], {})[score["trial"]] = score
    candidates, controls = arms["candidate"], arms[baseline]
    if not candidates or not controls or candidates.keys() != controls.keys():
        return {"status": "unavailable", "reason": "Complete matched case sets are required."}
    deltas = []
    families = {}
    for case_id in sorted(candidates):
        a, b = candidates[case_id], controls[case_id]
        if a.keys() != b.keys():
            return {"status": "unavailable", "reason": "Unequal repetition sets."}
        if any(s["outcome_status"] not in {"passed", "failed"} for s in [*a.values(), *b.values()]):
            return {"status": "unavailable", "reason": "Human review or infrastructure resolution is still required; no selective dropping."}
        delta = statistics.mean(int(a[k]["outcome_status"] == "passed") - int(b[k]["outcome_status"] == "passed") for k in sorted(a))
        deltas.append(delta)
        families.setdefault(next(iter(a.values()))["family"], []).append(delta)
    estimate = statistics.mean(deltas)
    result = {"status": "estimated", "case_count": len(deltas), "family_count": len(families), "delta": estimate, "interval": None, "confidence": 0.95, "seed": seed, "bootstrap_samples": samples}
    if len(deltas) < 5 or len(families) < 5:
        result["note"] = "Fewer than five independent scenario families: descriptive delta only."
        return result
    # Resample scenario families, keeping all within-family cases/repetitions paired.
    clusters = list(families.values())
    rng = random.Random(seed)
    boot = []
    for _ in range(samples):
        draw = [value for cluster in rng.choices(clusters, k=len(clusters)) for value in cluster]
        boot.append(statistics.mean(draw))
    boot.sort()
    if boot[0] == boot[-1]:
        result["note"] = "Every observed family has the same paired change. The empirical bootstrap has zero variance, so an uncertainty interval is suppressed; these authored scenarios do not establish population certainty."
        return result
    result["interval"] = [boot[int(samples * .025)], boot[min(samples - 1, int(samples * .975))]]
    result["note"] = "95% percentile bootstrap over scenario families; cases weighted equally, paired repetitions retained. Synthetic coverage is not production prevalence."
    return result


def wilson(successes, total, z=1.959963984540054):
    if not total:
        return None
    p = successes / total
    denominator = 1 + z*z / total
    center = (p + z*z/(2*total)) / denominator
    half = z * math.sqrt(p*(1-p)/total + z*z/(4*total*total)) / denominator
    return [center-half, center+half]


def build_report(scores, manifest):
    by_arm = collections.defaultdict(list)
    for score in scores:
        by_arm[score["arm"]].append(score)
    summaries = {}
    lines = ["# Skill evaluation report", "", "This report grades the frozen local run. A partial pilot does not certify the collection for release.", "", "| Arm | Planned | Passed | Failed | Needs review | Infrastructure | All repetitions passed |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for arm, values in sorted(by_arm.items()):
        counts = collections.Counter(s["status"] for s in values)
        cases = collections.defaultdict(list)
        for s in values:
            cases[s["case_id"]].append(s)
        all_pass = sum(all(s["status"] == "passed" for s in trials) for trials in cases.values())
        durations = [s["duration_seconds"] for s in values if isinstance(s.get("duration_seconds"), (int, float))]
        tokens = {k: sum(s.get("usage", {}).get(k, 0) or 0 for s in values) for k in ("input_tokens", "output_tokens", "cached_input_tokens")}
        usage_complete = all(s["status"] != "infra_error" and all(k in s.get("usage", {}) for k in ("input_tokens", "output_tokens", "cached_input_tokens")) for s in values)
        error_counts = collections.Counter(e["code"] for s in values for e in s.get("observed_tool_errors", []))
        summaries[arm] = {"planned": len(values), "counts": dict(counts), "case_count": len(cases), "all_repetitions_passed": all_pass, "median_duration_seconds": statistics.median(durations) if durations else None, "usage": tokens, "token_accounting_complete": usage_complete, "observed_tool_errors_by_code": dict(error_counts)}
        lines.append(f"| {arm} | {len(values)} | {counts['passed']} | {counts['failed']} | {counts['needs_review']} | {counts['infra_error']} | {all_pass}/{len(cases)} |")
    candidate = by_arm.get("candidate", [])
    routing = collections.Counter()
    for score in candidate:
        for check in score["checks"]:
            if check["kind"] != "activation":
                continue
            expected, observed = check.get("expected"), check.get("observed")
            if observed is None:
                routing["unknown"] += 1
            else:
                routing[{(True, True): "true_positive", (False, False): "true_negative", (True, False): "false_negative", (False, True): "false_positive"}[(expected, observed)]] += 1
    tp, fp, fn = routing["true_positive"], routing["false_positive"], routing["false_negative"]
    has_negatives = bool(fp + routing["true_negative"])
    routing_summary = {**routing, "negative_routing_coverage": has_negatives, "precision": tp/(tp+fp) if tp+fp and has_negatives else None, "recall": tp/(tp+fn) if tp+fn else None}
    full = bool(manifest.get("full_suite", False))
    repeated = bool(candidate) and min(collections.Counter(s["case_id"] for s in candidate).values()) >= 3
    has_holdout = any(s["split"] == "holdout" for s in candidate)
    all_passed = bool(candidate) and all(s["status"] == "passed" for s in candidate)
    baseline_complete = bool(by_arm.get("baseline")) and all(s["outcome_status"] in {"passed", "failed"} for s in by_arm["baseline"])
    estimate = paired_estimate(scores)
    release = "passed" if full and repeated and has_holdout and all_passed and baseline_complete and estimate["status"] == "estimated" else "not_ready"
    critical = [{"case_id": s["case_id"], "arm": s["arm"], "trial": s["trial"], "check": c["id"]} for s in scores for c in s["checks"] if c["severity"] == "critical" and c["status"] == "failed"]
    lines.extend(["", f"Release gate: **{release}**. Requires the entire frozen suite, at least three repetitions per case, held-out coverage, every candidate check passed, and fully adjudicated paired baseline evidence. This conservative repository policy is a starting threshold, not a statistical guarantee.", "", "## Candidate versus no-skill baseline", "", json_description(estimate)])
    if "previous" in by_arm:
        lines.extend(["", "## Candidate versus previous version", "", json_description(paired_estimate(scores, baseline="previous"))])
    lines.extend(["", "## Candidate routing", "", f"Observed activation checks: {dict(routing)}. Precision: {routing_summary['precision']}; recall: {routing_summary['recall']}. Precision is suppressed without negative routing cases. Unknown instrumentation stays separate. Repeated and correlated checks do not constitute independent production samples.", "", "## Candidate coverage", "", "| Split / workflow | Trials | Passed | Failed | Needs review | Infrastructure |", "| --- | ---: | ---: | ---: | ---: | ---: |"])
    groups = collections.defaultdict(list)
    for score in candidate:
        groups[f"{score['split']} / {score['workflow']}"].append(score)
    for group, values in sorted(groups.items()):
        counts = collections.Counter(s["status"] for s in values)
        lines.append(f"| {group} | {len(values)} | {counts['passed']} | {counts['failed']} | {counts['needs_review']} | {counts['infra_error']} |")
    lines.extend(["", "## Reliability and efficiency", "", "‘All repetitions passed’ is observed consistency over this run, not an estimated pass^k guarantee. We do not select the best attempt or rerun away a failure. Token totals include cached input separately; latency is host-dependent and no dollar cost is inferred. For runs with infrastructure errors or missing terminal usage, observed token totals are lower bounds, not evidence of zero consumption."])
    for arm, data in sorted(summaries.items()):
        lines.append(f"\n- {arm}: median trial seconds {data['median_duration_seconds']}; observed tokens {data['usage']}; accounting complete: {data['token_accounting_complete']}.")
        lines.append(f"  Observed tool errors (including deliberately injected fixture errors): {data['observed_tool_errors_by_code']}. Recovery is assessed by case-specific outcome checks; a permitted successful retry is not automatically a task failure.")
    failures = [(s, c) for s in scores for c in s["checks"] if c["status"] in {"failed", "needs_review"}]
    lines.extend(["", "## Outstanding results", ""])
    for score, check in failures:
        lines.append(f"- `{score['case_id']}/{score['arm']}/{score['trial']}/{check['id']}` — {check['status']}: {check['detail']}")
    for score in scores:
        if score["status"] == "infra_error":
            lines.append(f"- `{score['case_id']}/{score['arm']}/{score['trial']}` — infrastructure: {score.get('error')}")
    if not failures and not any(s["status"] == "infra_error" for s in scores):
        lines.append("No outstanding checks in the selected run.")
    summary = {"release_gate": release, "full_suite": full, "minimum_three_repeats": repeated, "holdout_present": has_holdout, "arms": summaries, "paired_comparison": estimate, "routing": routing_summary, "critical_failures": critical}
    return "\n".join(lines) + "\n", summary


def json_description(result):
    if result["status"] == "unavailable":
        return f"No quality-lift estimate: {result['reason']}"
    text = f"Mean paired change: {result['delta']:+.1%} across {result['case_count']} cases ({result['family_count']} scenario families)."
    if result["interval"]:
        text += f" 95% interval: {result['interval'][0]:+.1%} to {result['interval'][1]:+.1%}."
    return text + " " + result["note"]
