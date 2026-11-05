"""Independent examples for segment labels, coverage, and state safety."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skills/crunchbase-market-radar/scripts/radar.py"
spec = importlib.util.spec_from_file_location("gtm_radar", SCRIPT)
radar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(radar)


def fixture():
    data = {"schema_version": radar.SCHEMA, "as_of": "2026-11-05", "scope": {"market": "Fictional tools", "geography": "worldwide"},
            "segments": [], "organizations": [], "rounds": [], "coverage": {}}
    for sid, current in (("alpha", 20), ("beta", 10), ("gamma", 0)):
        data["segments"].append({"uuid": sid, "name": sid.title()})
        for i in range(15):
            data["organizations"].append({"uuid": f"{sid}-{i}", "segment_ids": [sid], "founded_on": "2010-01-01", "growth_tier": "p100_positive_high", "funding_tier": None})
        for period, count, day in (("prior", 12, "2025-01-01"), ("current", current, "2026-01-01")):
            for i in range(count):
                data["rounds"].append({"uuid": f"{sid}-{period}-{i}", "organization_uuid": f"{sid}-{i % 15}", "announced_on": day, "money_raised_usd": 100})
    for key in ("segments", "organizations", "rounds"):
        data["coverage"][key] = {"complete": True, "reported_count": len(data[key])}
    return data


class RadarTests(unittest.TestCase):
    def test_independent_direction_example(self):
        result = radar.analyze(fixture())
        labels = {s["uuid"]: s["label"] for s in result["segments"]}
        self.assertEqual(labels, {"alpha": "growing", "beta": "steady", "gamma": "declining"})
        self.assertEqual(result["focus_segments"], ["alpha"])
        self.assertEqual(result["reconsider_segments"], ["gamma"])
        self.assertEqual(result["peer_count"], 3)

    def test_unknown_is_not_observed_zero_or_a_direction(self):
        data = fixture()
        data["organizations"][0]["growth_tier"] = None
        result = radar.analyze(data)
        self.assertEqual(result["status"], "insufficient_comparable_segments")
        alpha = next(s for s in result["segments"] if s["uuid"] == "alpha")
        self.assertEqual(alpha["status"], "insufficient_evidence")
        self.assertIsNone(alpha["growth_share"])
        self.assertTrue(all(s["label"] is None for s in result["segments"]))

    def test_complete_means_reconciled_not_a_boolean_claim(self):
        for record in ({"complete": False, "reported_count": 45}, {"complete": True, "reported_count": 46}):
            data = fixture()
            data["coverage"]["organizations"] = record
            with self.assertRaises(ValueError):
                radar.analyze(data)

    def test_round_deduplication_and_order_invariance(self):
        data = fixture()
        expected = radar.analyze(data)
        data["rounds"].append(copy.deepcopy(data["rounds"][0]))
        for key in ("segments", "organizations", "rounds"):
            data[key].reverse()
        self.assertEqual(radar.analyze(data), expected)
        data["rounds"][0]["money_raised_usd"] = 999
        with self.assertRaisesRegex(ValueError, "conflicting duplicate"):
            radar.analyze(data)

    def test_future_dates_and_nonfinite_money_fail(self):
        for key, value in (("announced_on", "2027-01-01"), ("money_raised_usd", float("nan")), ("money_raised_usd", -1), ("money_raised_usd", True)):
            data = fixture()
            data["rounds"][0][key] = value
            with self.assertRaises(ValueError):
                radar.analyze(data)

    def test_boundary_windows_and_known_amount_coverage(self):
        data = fixture()
        data["rounds"][0]["announced_on"] = "2025-11-05"
        data["rounds"][0]["money_raised_usd"] = None
        data["rounds"][1]["money_raised_usd"] = 0
        result = radar.analyze(data)
        alpha = next(s for s in result["segments"] if s["uuid"] == "alpha")
        self.assertEqual(alpha["rounds_prior"], 12)
        self.assertEqual(alpha["money_prior"], {"known_usd": 1000, "known_amounts": 11, "unknown_amounts": 1})
        self.assertEqual(result["windows"]["current"][0], "2025-11-06")
        self.assertEqual(radar.months_back(radar.iso("2024-02-29", "date"), 12).isoformat(), "2023-02-28")

    def test_overlapping_territories_remain_multi_membership(self):
        data = fixture()
        data["organizations"][0]["segment_ids"].append("beta")
        data["account_uuids"] = ["alpha-0"]
        result = radar.analyze(data)
        self.assertEqual(result["territories"][0]["segment_uuids"], ["alpha", "beta"])

    def test_state_atomic_commit_idempotency_and_failed_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            source, state, output = directory / "input.json", directory / "state.json", directory / "out"
            data = fixture()
            source.write_text(json.dumps(data))
            args = [sys.executable, str(SCRIPT), "score", "--input", str(source), "--out-dir", str(output), "--state", str(state), "--write-state"]
            first = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            original = state.read_bytes()
            second = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(json.loads(second.stdout)["changes"], [])
            self.assertEqual(state.read_bytes(), original)
            data["coverage"]["rounds"]["complete"] = False
            source.write_text(json.dumps(data))
            failed = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(failed.returncode, 1)
            self.assertEqual(state.read_bytes(), original)
            self.assertTrue((output / "segments.csv").exists())

    def test_scope_change_is_new_baseline(self):
        data = fixture()
        first = radar.analyze(data)
        previous = {"schema_version": radar.SCHEMA, "rule_version": radar.RULE_VERSION, "as_of": first["as_of"], "scope_fingerprint": first["scope_fingerprint"], "labels": {s["uuid"]: "declining" for s in first["segments"]}}
        self.assertTrue(radar.analyze(data, previous)["changes"])
        data["scope"]["geography"] = "US"
        result = radar.analyze(data, previous)
        self.assertEqual(result["baseline_status"], "scope_changed")
        self.assertEqual(result["changes"], [])

    def test_book_policy_and_corrupt_state_are_not_silent_comparisons(self):
        data = fixture()
        data["account_uuids"] = ["alpha-0"]
        first = radar.analyze(data)
        data["account_uuids"] = ["beta-0"]
        self.assertNotEqual(first["scope_fingerprint"], radar.analyze(data)["scope_fingerprint"])
        previous = {"schema_version": radar.SCHEMA, "rule_version": radar.RULE_VERSION, "as_of": first["as_of"], "scope_fingerprint": first["scope_fingerprint"], "labels": {"alpha": "not-a-label"}}
        with self.assertRaisesRegex(ValueError, "labels"):
            radar.analyze(data, previous)

    def test_accepted_balanced_policy_assigns_each_account_once(self):
        data = fixture()
        data["territory_policy"] = "balanced-v1"
        data["account_uuids"] = [o["uuid"] for o in data["organizations"]]
        data["organizations"][0]["segment_ids"].append("beta")
        result = radar.analyze(data)
        self.assertEqual(len(result["territories"]), 45)
        self.assertTrue(all(row["territory_uuid"] in row["segment_uuids"] for row in result["territories"]))
        data["organizations"].reverse()
        self.assertEqual(result, radar.analyze(data))


if __name__ == "__main__":
    unittest.main()
