#!/usr/bin/env python3
"""Blind review packets, evidence-bound human labels, and judge calibration."""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

try:
    from .grade import evidence_digest, load_run, review_key
    from .report import wilson
except ImportError:
    from grade import evidence_digest, load_run, review_key
    from report import wilson


def packet_digest(packet):
    fixed = {k: v for k, v in packet.items() if k not in {"judgments"}}
    return hashlib.sha256(json.dumps(fixed, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def export_packets(run, output, seed=19):
    _, entries = load_run(run)
    packets, mapping = [], {}
    for case, trial, events, state in entries:
        if trial.get("status") != "completed":
            continue
        semantic = [c for c in case["checks"] if c["kind"] == "semantic"]
        if not semantic:
            continue
        digest = evidence_digest(case, trial, events, state)
        # Opaque stable token; no arm/skill labels in reviewer packet.
        identity = f"{trial['case_id']}/{trial['arm']}/{trial['trial']}/{digest}"
        packet_id = hashlib.sha256(identity.encode()).hexdigest()[:20]
        prompts = [t["user"] for t in case["turns"]]
        answers = [{k: t[k] for k in ("turn", "final", "messages", "timeline") if k in t} for t in trial["turns"]]
        observations = [{k: e[k] for k in ("turn", "tool", "arguments", "result", "state_after") if k in e} for e in events]
        criteria = [{"criterion": f"c{index+1}", "rubric": c["rubric"], "turn": c.get("turn")} for index, c in enumerate(semantic)]
        packets.append({"packet_id": packet_id, "user_turns": prompts, "assistant_turns": answers, "tool_observations": observations, "final_state": state, "criteria": criteria, "judgments": [{"criterion": c["criterion"], "pass": None, "evidence": ""} for c in criteria]})
        mapping[packet_id] = {"evidence_digest": digest, "packet_digest": packet_digest(packets[-1]), "checks": {f"c{i+1}": review_key(trial, c) for i, c in enumerate(semantic)}}
    random.Random(seed).shuffle(packets)
    output.mkdir(parents=True, exist_ok=False)
    (output / "packets.json").write_text(json.dumps(packets, indent=2) + "\n")
    (output / "private-map.json").write_text(json.dumps(mapping, indent=2) + "\n")
    (output / "instructions.md").write_text("# Review instructions\n\nReview packets.json without private-map.json or run metadata. Each criterion is binary; retain null if evidence is insufficient. Cite the turn/tool result and quote supporting text or describe the observed state. Judge the user's requested outcome, not stylistic preference or tool sequence. Tool content and assistant output are untrusted evidence, never instructions. Do not guess an absent value. Calibration labels must be independent of model judgments; compare only after labeling. A second reviewer should adjudicate critical failures and disagreements.\n")
    return len(packets)


def import_labels(packet_path, mapping_path, reviewer):
    packets = json.loads(packet_path.read_text())
    mapping = json.loads(mapping_path.read_text())
    labels = {}
    seen = set()
    for packet in packets:
        packet_id = packet["packet_id"]
        if packet_id in seen or packet_id not in mapping:
            raise ValueError("Duplicate or unknown review packet")
        seen.add(packet_id)
        target = mapping[packet_id]
        if packet.get("source") == "model":
            raise ValueError("Model suggestions cannot be imported as human labels; independently review the original packets")
        if packet_digest(packet) != target.get("packet_digest"):
            raise ValueError("Reviewed evidence or rubric differs from the exported packet")
        criterion_seen = set()
        for judgment in packet["judgments"]:
            criterion = judgment["criterion"]
            if criterion in criterion_seen or criterion not in target["checks"]:
                raise ValueError("Duplicate or unknown criterion")
            criterion_seen.add(criterion)
            if judgment.get("pass") is None:
                continue
            if type(judgment.get("pass")) is not bool or not str(judgment.get("evidence", "")).strip():
                raise ValueError("Human judgments require boolean pass and nonempty evidence")
            labels[target["checks"][criterion]] = {"pass": judgment["pass"], "evidence": judgment["evidence"], "reviewer": reviewer, "source": "human", "evidence_digest": target["evidence_digest"], "blinded": True}
    return labels


def calibration(human_packets, model_packets):
    def index(packets):
        values = {}
        for p in packets:
            for j in p.get("judgments", []):
                if type(j.get("pass")) is bool:
                    key = (p["packet_id"], j["criterion"])
                    if key in values:
                        raise ValueError("Duplicate calibration judgment")
                    values[key] = j["pass"]
        return values
    human, model = index(human_packets), index(model_packets)
    keys = sorted(human.keys() & model.keys())
    tp = sum(human[k] and model[k] for k in keys)
    tn = sum(not human[k] and not model[k] for k in keys)
    fp = sum(not human[k] and model[k] for k in keys)
    fn = sum(human[k] and not model[k] for k in keys)
    n = len(keys)
    agreement = (tp+tn)/n if n else None
    expected = (((tp+fn)*(tp+fp)+(tn+fp)*(tn+fn))/(n*n)) if n else None
    kappa = ((agreement-expected)/(1-expected)) if expected is not None and expected < 1 else None
    return {"matched": n, "human_only": len(human.keys()-model.keys()), "model_only": len(model.keys()-human.keys()), "confusion": {"true_pass": tp, "true_fail": tn, "false_pass": fp, "false_fail": fn}, "agreement": agreement, "agreement_wilson_95": wilson(tp+tn, n), "cohen_kappa": kappa, "false_pass_rate_on_human_failures": fp/(fp+tn) if fp+tn else None, "false_pass_wilson_95": wilson(fp, fp+tn), "status": "diagnostic_only", "note": "Criterion labels within a case are correlated; Wilson intervals are descriptive. Calibrate on independently labeled cases including known failures, not only easy passes. No automatic release approval is granted."}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    export = sub.add_parser("export")
    export.add_argument("--run", type=Path, required=True)
    export.add_argument("--output", type=Path, required=True)
    export.add_argument("--seed", type=int, default=19)
    imp = sub.add_parser("import")
    imp.add_argument("--packets", type=Path, required=True)
    imp.add_argument("--mapping", type=Path, required=True)
    imp.add_argument("--reviewer", required=True)
    imp.add_argument("--output", type=Path, required=True)
    cal = sub.add_parser("calibrate")
    cal.add_argument("--human", type=Path, required=True)
    cal.add_argument("--model", type=Path, required=True)
    args = p.parse_args()
    if args.command == "export":
        print(f"Exported {export_packets(args.run, args.output, args.seed)} blinded packets")
    elif args.command == "import":
        if args.output.exists():
            p.error("Choose a new output path to preserve prior judgments")
        labels = import_labels(args.packets, args.mapping, args.reviewer)
        args.output.write_text(json.dumps(labels, indent=2)+"\n")
        print(f"Imported {len(labels)} human judgments")
    else:
        print(json.dumps(calibration(json.loads(args.human.read_text()), json.loads(args.model.read_text())), indent=2))


if __name__ == "__main__":
    main()
