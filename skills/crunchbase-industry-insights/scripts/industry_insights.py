#!/usr/bin/env python3
"""Deterministic GTM segment comparison from complete normalized records (stdlib)."""
import argparse
import calendar
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import sys
import tempfile
from datetime import date, timedelta

SCHEMA = "crunchbase-industry-insights/1"
RULE_VERSION = "gtm-direction/1"
TIERS = {"p100_positive_high", "p200_positive_low", "p300_neutral", "p400_negative_low", "p500_negative_high"}
DIRECTIONS = {"c100_growing": "Growing", "c200_stable": "Stable", "c300_declining": "Declining"}


def iso(value, field):
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError(field + " must be a full ISO date")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(field + " must be a full ISO date") from exc


def months_back(day, months):
    year, month0 = divmod(day.year * 12 + day.month - 1 - months, 12)
    return date(year, month0 + 1, min(day.day, calendar.monthrange(year, month0 + 1)[1]))


def unique(rows, kind):
    if not isinstance(rows, list):
        raise ValueError(kind + " must be a list")
    found = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("uuid"), str) or not row["uuid"]:
            raise ValueError(kind + " requires canonical uuid")
        key = row["uuid"]
        if key in found and found[key] != row:
            raise ValueError("conflicting duplicate " + kind + " " + key)
        found[key] = row
    return [found[key] for key in sorted(found)]


def complete(coverage, name, rows):
    record = coverage.get(name, {})
    if record.get("complete") is not True or type(record.get("reported_count")) is not int:
        raise ValueError(name + " coverage must be complete with reported_count")
    if record["reported_count"] != len(rows):
        raise ValueError(name + " reported_count differs from unique retrieved records")


def ratio(value, middle):
    # Preserve the original rule's finite zero-baseline convention.
    return value / middle if middle else (1.0 if value == 0 else 2.0)


def direction(rel, z, growth_ratio, youth_ratio, young):
    if rel <= -0.20 and z <= -1.5:
        return "declining", "D1"
    if rel <= -0.10 and z <= -1 and growth_ratio < 1:
        return "declining", "D2"
    if youth_ratio >= 1.5 and rel >= 0 and young >= 5:
        return "emerging", "E1"
    if rel >= 0.10 and z >= 1:
        return "growing", "G1"
    if rel >= 0 and growth_ratio >= 1.25:
        return "growing", "G2"
    return "steady", "S1"


def amount_summary(rounds):
    values = [r["money_raised_usd"] for r in rounds if r.get("money_raised_usd") is not None]
    return {"known_usd": sum(values) if values or not rounds else None,
            "known_amounts": len(values), "unknown_amounts": len(rounds) - len(values)}


def assign_territories(rows, policy):
    """Accepted greedy balanced partition; retain memberships alongside assignment."""
    if policy == "memberships":
        return rows
    if policy != "balanced-v1":
        raise ValueError("territory_policy must be memberships or balanced-v1")
    pending = {r["organization_uuid"]: r for r in rows if r["segment_uuids"]}
    cap = max(1, math.ceil(len(pending) * 0.4))
    selected = []
    while pending and len(selected) < 10:
        tally = {}
        for row in pending.values():
            for sid in row["segment_uuids"]:
                tally[sid] = tally.get(sid, 0) + 1
        bounded = [(sid, count) for sid, count in tally.items() if count <= cap]
        sid, _ = min(bounded or list(tally.items()), key=lambda pair: (-pair[1], pair[0]))
        selected.append(sid)
        matched = [key for key, row in pending.items() if sid in row["segment_uuids"]]
        for key in matched:
            pending.pop(key)["territory_uuid"] = sid
    for row in rows:
        row.setdefault("territory_uuid", None)
        row["territory_status"] = "assigned" if row["territory_uuid"] else "other"
    return rows


def analyze(data, previous=None):
    if data.get("schema_version") != SCHEMA:
        raise ValueError("unsupported schema_version")
    today = iso(data.get("as_of"), "as_of")
    scope = data.get("scope")
    if not isinstance(scope, dict) or not scope:
        raise ValueError("scope must describe the agreed universe")
    segments = unique(data.get("segments"), "segments")
    organizations = unique(data.get("organizations"), "organizations")
    rounds = unique(data.get("rounds"), "rounds")
    coverage = data.get("coverage")
    if not isinstance(coverage, dict):
        raise ValueError("coverage is required")
    for key, records in (("segments", segments), ("organizations", organizations), ("rounds", rounds)):
        complete(coverage, key, records)
    ids = {s["uuid"] for s in segments}
    org_ids = {o["uuid"] for o in organizations}
    for seg in segments:
        if not isinstance(seg.get("name"), str) or not seg["name"]:
            raise ValueError("segment name required")
    for org in organizations:
        memberships = org.get("segment_ids")
        if not isinstance(memberships, list) or not all(isinstance(x, str) for x in memberships):
            raise ValueError("organization segment_ids required")
        # Organizations can also belong to segments outside the agreed comparison.
        for field in ("growth_tier", "funding_tier"):
            if org.get(field) is not None and org[field] not in TIERS:
                raise ValueError("unknown " + field)
        if org.get("founded_on") is not None and iso(org["founded_on"], "founded_on") > today:
            raise ValueError("future founded_on")
    for row in rounds:
        if row.get("organization_uuid") not in org_ids:
            raise ValueError("round organization outside retrieved universe")
        if iso(row.get("announced_on"), "announced_on") > today:
            raise ValueError("future completed funding round")
        money = row.get("money_raised_usd")
        if money is not None and (isinstance(money, bool) or not isinstance(money, (int, float)) or not math.isfinite(money) or money < 0):
            raise ValueError("money_raised_usd must be finite nonnegative USD or null")
    cut12, cut24, young_cut = months_back(today, 12), months_back(today, 24), months_back(today, 36)
    results = []
    for seg in segments:
        members = [o for o in organizations if seg["uuid"] in o["segment_ids"]]
        member_ids = {o["uuid"] for o in members}
        relevant = [r for r in rounds if r["organization_uuid"] in member_ids]
        current = [r for r in relevant if cut12 < iso(r["announced_on"], "announced_on") <= today]
        prior = [r for r in relevant if cut24 < iso(r["announced_on"], "announced_on") <= cut12]
        growth_known = [o for o in members if o.get("growth_tier") is not None]
        youth_known = [o for o in members if o.get("founded_on") is not None]
        raise_known = [o for o in members if o.get("funding_tier") is not None]
        n = len(members)
        growth = sum(o["growth_tier"] == "p100_positive_high" for o in growth_known)
        young = sum(iso(o["founded_on"], "founded_on") >= young_cut for o in youth_known)
        raises = sum(o["funding_tier"] in {"p100_positive_high", "p200_positive_low"} for o in raise_known)
        sufficient = n >= 15 and len(current) + len(prior) >= 12 and len(prior) >= 5
        known = len(growth_known) == n and len(youth_known) == n
        status = "eligible" if sufficient and known else "insufficient_evidence" if not known else "too_small"
        results.append({"uuid": seg["uuid"], "name": seg["name"], "url": seg.get("url"),
                        "companies": n, "organization_uuids": sorted(member_ids),
                        "rounds_current": len(current), "rounds_prior": len(prior),
                        "money_current": amount_summary(current), "money_prior": amount_summary(prior),
                        "growth_known": len(growth_known), "founding_known": len(youth_known), "funding_prediction_known": len(raise_known),
                        "very_likely_growth": growth, "young": young,
                        "growth_share": growth / n if n and len(growth_known) == n else None,
                        "young_share": young / n if n and len(youth_known) == n else None,
                        "raise_share": raises / n if n and len(raise_known) == n else None,
                        "deal_change": len(current) / len(prior) - 1 if prior else None,
                        "status": status, "label": None, "score": None, "rule": None})
    eligible = [s for s in results if s["status"] == "eligible"]
    comparable = len(eligible) >= 3
    medians = {}
    if comparable:
        medians = {k: statistics.median(s[k] for s in eligible) for k in ("deal_change", "growth_share", "young_share")}
        # Optional predictions affect ordering only when equally observed in every peer.
        medians["raise_share"] = statistics.median(s["raise_share"] for s in eligible) if all(s["raise_share"] is not None for s in eligible) else None
        for seg in eligible:
            rel = seg["deal_change"] - medians["deal_change"]
            expected = seg["rounds_prior"] * (1 + medians["deal_change"])
            z = (seg["rounds_current"] - expected) / math.sqrt(expected) if expected > 0 else 0.0
            gr = ratio(seg["growth_share"], medians["growth_share"])
            yr = ratio(seg["young_share"], medians["young_share"])
            label, rule = direction(rel, z, gr, yr, seg["young"])
            raise_term = 0.5 * (seg["raise_share"] - medians["raise_share"]) if medians["raise_share"] is not None else 0
            score = rel + seg["growth_share"] - medians["growth_share"] + 0.5 * (seg["young_share"] - medians["young_share"]) + raise_term
            seg.update(label=label, rule=rule, score=round(score, 6), relative_change=rel, z=z,
                       growth_ratio=gr, youth_ratio=yr, watch_instead_of_cut=label == "declining" and (gr >= 1.25 or yr >= 1.5))
    latest = {}
    for insight in data.get("insights", []):
        sid = insight.get("segment_uuid")
        if sid not in ids or insight.get("direction") not in DIRECTIONS:
            raise ValueError("insight requires known segment and direction")
        generated = iso(insight.get("generated_on"), "generated_on")
        if generated > today:
            raise ValueError("future insight")
        if sid in latest and latest[sid]["generated_on"] == insight["generated_on"] and latest[sid] != insight:
            raise ValueError("conflicting insight at same date")
        if sid not in latest or latest[sid]["generated_on"] < insight["generated_on"]:
            latest[sid] = insight
    order = {"emerging": 0, "growing": 0, "steady": 1, "declining": 2, None: 3}
    results.sort(key=lambda s: (order[s["label"]], -(s["score"] or 0), s["uuid"]))
    for seg in results:
        seg["crunchbase_call"] = latest.get(seg["uuid"])
    focus = [s["uuid"] for s in results if s["label"] in {"emerging", "growing"}][:3]
    reconsider = [s["uuid"] for s in sorted(results, key=lambda s: (s["score"] or 0, s["uuid"]))
                  if s["label"] == "declining" and not s["watch_instead_of_cut"]][:3]
    watch = data.get("watch_segment_uuids", sorted(ids))
    if not isinstance(watch, list) or any(sid not in ids for sid in watch):
        raise ValueError("watch_segment_uuids must identify retrieved segments")
    account_ids = data.get("account_uuids", [])
    if not isinstance(account_ids, list) or any(x not in org_ids for x in account_ids):
        raise ValueError("account_uuids must be resolved organizations in the universe")
    territory_policy = data.get("territory_policy", "memberships")
    if territory_policy not in {"memberships", "balanced-v1"}:
        raise ValueError("unknown territory policy")
    fingerprint = hashlib.sha256(json.dumps({"scope": scope, "segments": sorted(ids), "watch": sorted(set(watch)), "rule": RULE_VERSION,
                                            "accounts": sorted(set(account_ids)), "territory_policy": territory_policy}, sort_keys=True).encode()).hexdigest()
    changes, baseline = [], "initial"
    if previous is not None:
        if previous.get("schema_version") != SCHEMA or not isinstance(previous.get("labels"), dict):
            raise ValueError("invalid previous state")
        if previous.get("rule_version") != RULE_VERSION:
            raise ValueError("previous state uses an unsupported rule version")
        if any(not isinstance(key, str) or not key or label not in {None, "emerging", "growing", "steady", "declining"}
               for key, label in previous["labels"].items()):
            raise ValueError("invalid previous state labels")
        calls = previous.get("market_calls", {})
        if not isinstance(calls, dict) or any(key not in previous["labels"] or call not in {None, *DIRECTIONS} for key, call in calls.items()):
            raise ValueError("invalid previous market calls")
        if not isinstance(previous.get("scope_fingerprint"), str) or len(previous["scope_fingerprint"]) != 64:
            raise ValueError("invalid previous scope fingerprint")
        if iso(previous.get("as_of"), "previous.as_of") > today:
            raise ValueError("state is newer than current analysis")
        baseline = "comparable" if previous.get("scope_fingerprint") == fingerprint else "scope_changed"
        if baseline == "comparable" and comparable:
            for seg in results:
                old = previous["labels"].get(seg["uuid"])
                new = seg["label"]
                if seg["uuid"] in watch and old is not None and new is not None and old != new:
                    changes.append({"segment_uuid": seg["uuid"], "kind": "direction", "previous": old, "current": new})
                old_call = previous.get("market_calls", {}).get(seg["uuid"])
                new_call = (seg.get("crunchbase_call") or {}).get("direction")
                if seg["uuid"] in watch and old is not None and new is not None and old_call and new_call and old_call != new_call and "c300_declining" in (old_call, new_call):
                    changes.append({"segment_uuid": seg["uuid"], "kind": "crunchbase_call", "previous": old_call, "current": new_call})
    territories = [{"organization_uuid": o["uuid"], "name": o.get("name"), "url": o.get("url"),
                    "segment_uuids": sorted(set(o["segment_ids"]) & ids)} for o in organizations if o["uuid"] in set(account_ids)]
    territories = assign_territories(territories, territory_policy)
    return {"schema_version": SCHEMA, "rule_version": RULE_VERSION, "as_of": today.isoformat(), "scope": scope,
            "coverage": coverage, "status": "complete" if comparable else "insufficient_comparable_segments",
            "windows": {"current": [(cut12 + timedelta(days=1)).isoformat(), today.isoformat()], "prior": [(cut24 + timedelta(days=1)).isoformat(), cut12.isoformat()], "young_since": young_cut.isoformat()},
            "peer_count": len(eligible), "peer_medians": medians, "segments": results,
            "focus_segments": focus, "reconsider_segments": reconsider, "territories": territories, "territory_policy": territory_policy,
            "changes": changes, "baseline_status": baseline, "scope_fingerprint": fingerprint,
            "limitations": ["Segment memberships overlap; do not sum segment money or company counts as a market total.",
                            "Direction labels and z thresholds are descriptive heuristics, not statistical significance or buyer demand."]}


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".radar-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def safe_cell(value):
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["score"])
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--state", type=Path)
    parser.add_argument("--write-state", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.write_state and args.state is None:
            raise ValueError("--write-state requires --state")
        previous = json.loads(args.state.read_text()) if args.state and args.state.exists() else None
        result = analyze(json.loads(args.input.read_text()), previous)
        args.out_dir.mkdir(parents=True, exist_ok=True)
        atomic_json(args.out_dir / "result.json", result)
        fields = ["uuid", "name", "status", "label", "score", "companies", "rounds_current", "rounds_prior", "growth_known", "founding_known", "growth_share", "young_share", "raise_share"]
        with (args.out_dir / "segments.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows({key: safe_cell(seg.get(key)) for key in fields} for seg in result["segments"])
        atomic_json(args.out_dir / "handoff.json", {"schema_version": "crunchbase-gtm-handoff/1", "as_of": result["as_of"], "scope": result["scope"], "coverage": result["coverage"], "segment_uuids": result["focus_segments"], "source": "crunchbase-industry-insights", "scope_confirmed": True, "segment_selection_status": "proposed", "execution_authorized": False})
        if args.write_state and result["status"] == "complete":
            atomic_json(args.state, {"schema_version": SCHEMA, "rule_version": RULE_VERSION, "as_of": result["as_of"], "scope_fingerprint": result["scope_fingerprint"], "labels": {s["uuid"]: s["label"] for s in result["segments"]}, "market_calls": {s["uuid"]: (s.get("crunchbase_call") or {}).get("direction") for s in result["segments"]}})
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 0 if result["status"] == "complete" else 2
    except (ValueError, TypeError, OSError, KeyError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
