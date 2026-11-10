"""Independent edge examples for sales briefs and stateful account monitoring."""
from __future__ import annotations
import copy
from datetime import date
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


pulse = module("pulse_workflow", "skills/crunchbase-account-pulse/scripts/pulse.py")
brief = module("intel_validator", "skills/crunchbase-account-intel/scripts/validate_brief.py")


class PulseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        self.account = {"uuid": "company-1", "permalink": "fictional-one", "name": "Fictional One",
                        "url": "https://www.crunchbase.com/organization/fictional-one", "website_url": "https://one.invalid",
                        "growth_score": 80, "heat_score_delta_d90": 8, "growth_prediction_tier": "p300_neutral", "tier": "A"}
        self.event = {"kind": "funding", "id": "round-1", "org": "fictional-one", "date": "2026-10-06",
                      "created": "2026-10-06", "round": "series_b", "amount_usd": 100,
                      "source": "https://www.crunchbase.com/funding_round/round-1"}

    def write(self, name, obj):
        path = self.work / name
        path.write_text(json.dumps(obj))
        return str(path)

    def args(self, records=None, accounts=None, **changes):
        records = [self.event] if records is None else records
        accounts = [self.account] if accounts is None else accounts
        counts = {}
        for rec in records:
            coll = pulse.COMPACT_COLLECTIONS[rec["kind"]]
            counts.setdefault(coll, set()).add(rec.get("id") or json.dumps(rec, sort_keys=True))
        cols = {c: {"retrieved": len(ids), "total": len(ids), "complete": True} for c, ids in counts.items()}
        cols.setdefault("funding_rounds", {"retrieved": 0, "total": 0, "complete": True})
        cols.setdefault("layoffs", {"retrieved": 0, "total": 0, "complete": True})
        cov = {"schema_version": "pulse-coverage/v1", "as_of": "2026-11-05", "accounts": {"requested": len(accounts), "confirmed": len(accounts)}, "collections": cols}
        values = dict(today="2026-11-05", lookback=90, signals="funding", focus=None, buyer_titles=None,
                      accounts=self.write("accounts.json", {"schema_version": "pulse-accounts/v1", "accounts": accounts}),
                      data=[self.write("events.json", records)], coverage=self.write("coverage.json", cov),
                      state=None, write_state=False, top=10, plays_window=60, plays_scope=None,
                      alert_scope="all", feed_dir=None, feed_all=False, list_csv=None,
                      since=None, out=None)
        values.update(changes)
        return SimpleNamespace(**values)

    def test_independent_half_life_example(self):
        # 30-day Series B: 40 * .5 = 20; growth 8 + heat 2; Tier A 10 => 40.
        result = pulse.run_rank(self.args())
        self.assertEqual(result["ranked"][0]["score"], 40)
        self.assertTrue(result["complete"])
        self.assertEqual(result["ranked"][0]["uuid"], "company-1")

    def test_inclusive_event_and_play_window_boundaries(self):
        for days, included, excluded in [(1, "2026-11-05", "2026-11-04"),
                                         (60, "2026-09-07", "2026-09-06")]:
            with self.subTest(days=days):
                for event_date, expected in [("2026-11-05", True), (included, True), (excluded, False)]:
                    result = pulse.run_rank(self.args([{**self.event, "date": event_date}], lookback=days, plays_window=days))
                    self.assertEqual(result["window_start"], included)
                    self.assertEqual(bool(result["ranked"][0]["signals"]), expected)
                    self.assertEqual(result["scope"]["window_policy"], "inclusive-calendar-days/v1")
                    # A wider event window isolates the play-window cutoff.
                    second = {**self.account, "uuid": "company-2", "permalink": "fictional-two", "url": "https://www.crunchbase.com/organization/fictional-two"}
                    wider = pulse.run_rank(self.args([{**self.event, "date": event_date}, {**self.event, "id": "round-2", "org": "fictional-two", "date": event_date}], accounts=[self.account, second], lookback=90, plays_window=days, plays_scope="all"))
                    self.assertEqual(bool(wider["plays"]), expected)

    def test_old_window_policy_state_requires_new_baseline(self):
        import hashlib
        args = self.args(state=str(self.work / "old-state.json"), write_state=True, out=str(self.work / "result.json"))
        pulse.run_rank(args)
        path = Path(args.state); state = json.loads(path.read_text())
        result = pulse.run_rank(self.args())
        old_scope = dict(result["scope"]); old_scope.pop("window_policy")
        state["scope_fingerprint"] = hashlib.sha256(json.dumps(old_scope, sort_keys=True).encode()).hexdigest()
        path.write_text(json.dumps(state)); before = path.read_bytes()
        with self.assertRaisesRegex(ValueError, "scope changed"):
            pulse.run_rank(args)
        self.assertEqual(path.read_bytes(), before)

    def test_unknown_and_zero_differ(self):
        unknown = dict(self.account, growth_score=None)
        result = pulse.run_rank(self.args(accounts=[unknown]))
        self.assertIsNone(result["ranked"][0]["score"])
        self.assertIsNone(result["ranked"][0]["rank"])
        known = dict(self.account, growth_score=0, heat_score_delta_d90=0, tier="")
        result = pulse.run_rank(self.args(accounts=[known]))
        self.assertEqual(result["ranked"][0]["score"], 20)

    def test_future_event_not_replaced_with_created_or_today(self):
        ev = dict(self.event, date="2027-01-01", created="2026-11-05")
        result = pulse.run_rank(self.args(records=[ev]))
        self.assertEqual(result["stats"]["events"], 0)
        self.assertEqual(result["call_list"], [])
        self.assertFalse(result["complete"])
        self.assertEqual(len(result["rejected_observations"]), 1)

    def test_source_required(self):
        ev = dict(self.event, source=None)
        result = pulse.run_rank(self.args(records=[ev]))
        self.assertIsNone(result["ranked"][0]["score"])
        self.assertEqual(result["call_list"], [])

    def test_secondary_is_not_new_money(self):
        for kind in ("secondary_market", "post_ipo_secondary", "non_equity_assistance"):
            with self.subTest(kind=kind):
                result = pulse.run_rank(self.args(records=[dict(self.event, round=kind)]))
                self.assertEqual(result["call_list"], [])
                self.assertEqual(result["ranked"][0]["score_parts"]["signals"], 0)

    def test_partial_301_records_not_complete_at_300_limit(self):
        args = self.args()
        cov = json.loads(Path(args.coverage).read_text())
        cov["collections"]["funding_rounds"].update(total=301, complete=False)
        Path(args.coverage).write_text(json.dumps(cov))
        result = pulse.run_rank(args)
        self.assertFalse(result["complete"])
        self.assertIsNone(result["ranked"][0]["score"])
        self.assertEqual(result["alerts"], [])
        self.assertEqual(result["call_list"], [])
        self.assertEqual(result["plays"], [])
        self.assertEqual(result["raise_feed"], [])
        self.assertEqual(len(result["unranked_evidence"]), 1)

    def test_false_manifest_count_fails(self):
        args = self.args()
        cov = json.loads(Path(args.coverage).read_text())
        cov["collections"]["funding_rounds"].update(retrieved=2, total=2)
        Path(args.coverage).write_text(json.dumps(cov))
        with self.assertRaisesRegex(ValueError, "unique input"):
            pulse.run_rank(args)

    def test_baseline_then_new_signal_then_idempotent_rerun(self):
        state, out = str(self.work / "state.json"), str(self.work / "result.json")
        first = pulse.run_rank(self.args(state=state, out=out, write_state=True))
        self.assertTrue(first["baseline"])
        self.assertEqual(first["alerts"], [])
        new = dict(self.event, id="round-2", date="2026-11-05", created="2026-11-05")
        second = pulse.run_rank(self.args(records=[self.event, new], state=state, out=out, write_state=True))
        self.assertEqual(len(second["alerts"]), 1)
        self.assertEqual(second["alerts"][0]["items"][0]["id"], "round-2")
        third = pulse.run_rank(self.args(records=[self.event, new], state=state, out=out, write_state=True))
        self.assertEqual(third["alerts"], [])

    def test_invalid_event_does_not_advance_state(self):
        state, out = str(self.work / "state.json"), str(self.work / "result.json")
        pulse.run_rank(self.args(state=state, out=out, write_state=True))
        before = Path(state).read_bytes()
        with self.assertRaisesRegex(ValueError, "complete valid"):
            pulse.run_rank(self.args(records=[dict(self.event, date="2027-01-01")], state=state, out=out, write_state=True))
        self.assertEqual(Path(state).read_bytes(), before)

    def test_output_failure_does_not_advance_state(self):
        state, out = str(self.work / "state.json"), str(self.work / "result.json")
        pulse.run_rank(self.args(state=state, out=out, write_state=True))
        before = Path(state).read_bytes()
        with self.assertRaises(OSError):
            pulse.run_rank(self.args(state=state, out=str(self.work), write_state=True))
        self.assertEqual(Path(state).read_bytes(), before)

    def test_corrupt_and_changed_scope_state_fail_closed(self):
        state, out = str(self.work / "state.json"), str(self.work / "result.json")
        pulse.run_rank(self.args(state=state, out=out, write_state=True))
        before = Path(state).read_bytes()
        with self.assertRaisesRegex(ValueError, "scope changed"):
            pulse.run_rank(self.args(state=state, out=out, write_state=True, lookback=60))
        self.assertEqual(Path(state).read_bytes(), before)
        Path(state).write_text('{"version":1}')
        with self.assertRaisesRegex(ValueError, "unsupported or corrupt"):
            pulse.run_rank(self.args(state=state, out=out, write_state=True))

    def test_ambiguous_domain_and_name_only_remain_unresolved(self):
        orgs = [self.account, dict(self.account, uuid="company-2", permalink="fictional-two")]
        result = pulse.match_book({"rows": [{"domain": "one.invalid", "name": "Fictional One"}]}, orgs)
        self.assertEqual(result["accounts"], [])
        self.assertEqual(len(result["ambiguous"]), 1)
        result = pulse.match_book({"rows": [{"name": "Fictional One"}]}, [self.account])
        self.assertEqual(result["accounts"], [])
        self.assertEqual(len(result["unmatched"]), 1)

    def test_duplicate_event_and_permutation_invariance(self):
        other = dict(self.event, id="round-2", date="2026-11-04")
        a = pulse.run_rank(self.args(records=[self.event, other, self.event]))
        b = pulse.run_rank(self.args(records=[other, self.event]))
        self.assertEqual(a["ranked"], b["ranked"])
        self.assertEqual(a["stats"]["events"], 2)

    def test_conflicting_duplicate_event_fails_before_state(self):
        other = dict(self.event, round="secondary_market", amount_usd=999999)
        state = self.work / "state.json"
        with self.assertRaisesRegex(ValueError, "conflicting duplicate"):
            pulse.run_rank(self.args(records=[self.event, other], state=str(state), out=str(self.work / "out.json"), write_state=True))
        self.assertFalse(state.exists())

    def test_nonfinite_and_bool_momentum_are_unknown(self):
        for value in (float("nan"), float("inf"), True, -1, 101):
            with self.subTest(value=value):
                self.assertIsNone(pulse.momentum_points(dict(self.account, growth_score=value)))

    def test_prediction_without_history_not_new(self):
        pred = {"generated_on": date(2026, 11, 5), "tier": "p100_positive_high", "ts": {"months_00_to_05": .8}}
        self.assertTrue(pulse.is_positive(pred))
        self.assertFalse(pulse.turned_positive(pred, None))

    def test_same_day_prediction_conflict_is_conservative(self):
        good = {"org": "fictional-one", "generated_on": date(2026, 11, 5), "tier": "p100_positive_high", "ts": {"months_00_to_05": .9}}
        bad = dict(good, tier="p500_negative_high")
        for records in ([good, bad], [bad, good]):
            self.assertFalse(pulse.is_positive(pulse.summarize_predictions(records)["fictional-one"]["latest"]))

    def test_acquisition_very_likely_date_is_latest_reading(self):
        records = [{"kind": "acq_prediction", "id": "p-" + str(i), "org": "fictional-one", "generated_on": d, "tier": t}
                   for i, (d, t) in enumerate([("2026-10-01", "p500_negative_high"), ("2026-11-01", "p200_positive_low"), ("2026-11-05", "p100_positive_high")])]
        args = self.args(records=records, signals="acquisition")
        result = pulse.run_rank(args)
        self.assertEqual(result["call_list"][0]["signals"][0]["date"], "2026-11-05")
        self.assertEqual(result["alerts"][0]["items"][0]["date"], "2026-11-05")

    def test_future_since_fails_before_feed_files(self):
        folder = self.work / "feed"
        with self.assertRaisesRegex(ValueError, "since date"):
            pulse.run_rank(self.args(since="2027-01-01", feed_dir=str(folder)))
        self.assertFalse(folder.exists())

    def test_fund_uses_search_started_on(self):
        raw = {"uuid": "fund-1", "url": "https://www.crunchbase.com/fund_financial/fund-1", "properties": {"owner_identifier": {"permalink": "fictional-one"}, "started_on": "2026-11-01", "money_raised": {"value_usd": 25}}}
        ev = pulse.event_from_raw("funds", raw, date(2026, 11, 5))
        self.assertEqual(ev["date"], date(2026, 11, 1))
        self.assertEqual(ev["round"], "fund_start")
        self.assertFalse(ev["new_money"])

    def test_missing_growth_article_not_an_event(self):
        ev = {"organization": {"permalink": "fictional-one"}, "generated_on": "2026-11-05", "growth_indicators": ["customers"]}
        self.assertIsNone(pulse.growth_from_props(ev, "growth-1", date(2026, 11, 5)))

    def test_trace_shaped_flat_nested_and_array_records_are_equivalent(self):
        org = {"permalink": "fictional-one", "uuid": "company-1", "value": "Fictional One"}
        funding = {"identifier": {"uuid": "round-1", "permalink": "round-1"}, "funded_organization_identifier": org,
                   "announced_on": "2026-10-06", "investment_type": "series_b", "money_raised": {"value_usd": 100}}
        prediction = {"identifier": {"uuid": "prediction-1"}, "organization": org, "generated_on": "2026-11-01",
                      "probability_tier": "p100_positive_high", "probability_score_timeseries": {"months_00_to_05": .8}}
        person = {"identifier": {"uuid": "person-1", "permalink": "person-one", "value": "Person One"},
                  "primary_organization": org, "primary_job_title": "VP Product"}
        for props, convert in ((funding, lambda row: pulse.event_from_raw("funding_rounds", row, date(2026,11,5))),
                               (prediction, pulse.prediction_from_raw), (person, pulse.people_from_raw),
                               ({"identifier": org, "website_url": "https://one.invalid"}, pulse.org_from_entity)):
            identity = props["identifier"]["uuid"]
            url = "https://www.crunchbase.com/funding_round/round-1" if props is funding else None
            flat = dict(props, uuid=identity, url=url)
            nested = {"uuid": identity, "url": url, "properties": props}
            array = {"uuid": identity, "url": url, "properties": [{"field_id": k, "value": v} for k,v in props.items()]}
            self.assertIsNotNone(convert(flat))
            self.assertEqual(convert(flat), convert(nested))
            self.assertEqual(convert(flat), convert(array))

    def test_flat_search_response_reaches_ranked_result(self):
        args = self.args()
        raw = {"collection_id": "funding_rounds", "count": 1, "entities": [{"uuid": "round-1", "url": self.event["source"],
                "identifier": {"uuid": "round-1", "permalink": "round-1"},
                "funded_organization_identifier": {"permalink": "fictional-one", "uuid": "company-1"},
                "announced_on": "2026-10-06", "investment_type": "series_b", "money_raised": {"value_usd": 100}}]}
        args.data = [self.write("raw-search.json", raw)]
        result = pulse.run_rank(args)
        self.assertTrue(result["complete"])
        self.assertEqual(result["call_list"][0]["score"], 40)

    def test_duplicate_property_conflict_is_not_silently_normalized(self):
        with self.assertRaisesRegex(ValueError, "conflicting duplicate property"):
            pulse.properties_of({"properties": [{"field_id": "growth_score", "value": 10}, {"field_id": "growth_score", "value": 90}]})

    def test_tool_error_is_not_empty_success(self):
        with self.assertRaisesRegex(ValueError, "tool error"):
            list(pulse.iter_payloads({"isError": True, "content": []}))

    def test_csv_cells_cannot_execute_formulas(self):
        for value in ("=HYPERLINK(\"x\")", "  +1", "@cmd", "-cmd"):
            self.assertEqual(pulse.safe_cell(value), "'" + value)
        self.assertEqual(pulse.safe_cell(-5), -5)


class IntelTests(unittest.TestCase):
    def example(self):
        return {"schema_version": "account-intel/v2", "as_of": "2026-11-05",
                "company": {"uuid": "company-1", "name": "Fictional One", "permalink": "fictional-one", "url": "https://www.crunchbase.com/organization/fictional-one"},
                "scope": {"purpose": "sales meeting", "seller_mode": "product-neutral", "event_start": "2026-05-05", "event_end": "2026-11-05"},
                "coverage": {"complete": True, "limitations": [], "sources": ["Crunchbase"]},
                "meeting_type": "first", "summary": "Fictional example", "talking_points": [], "recent_events": [], "people": [], "competitors": [], "crm": None, "notes": []}

    def test_minimal_brief(self):
        self.assertTrue(brief.validate_brief(self.example())["valid"])

    def test_future_and_unsourced_events_rejected(self):
        for event in ({"date": "2027-01-01", "description": "future", "source_url": "https://example.invalid"}, {"date": "2026-11-01", "description": "event", "source_url": None}):
            obj = self.example(); obj["recent_events"] = [event]
            with self.assertRaises(ValueError):
                brief.validate_brief(obj)

    def test_canonical_url_mismatch_rejected(self):
        obj = self.example(); obj["company"]["url"] = "https://www.crunchbase.com/funding_round/fictional-one"
        with self.assertRaisesRegex(ValueError, "canonical organization"):
            brief.validate_brief(obj)

    def test_talking_point_requires_evidence_and_offering(self):
        obj = self.example(); obj["scope"]["seller_mode"] = "tailored"
        obj["talking_points"] = [{"fact": [{"date": "2026-11-01", "fact": "announced a product", "source_url": "https://example.invalid/news"}], "implication": "may matter", "say": "Ask about it"}]
        with self.assertRaisesRegex(ValueError, "confirmed offering"):
            brief.validate_brief(obj)
        obj["talking_points"][0]["seller_offering"] = "User-supplied product"
        self.assertTrue(brief.validate_brief(obj)["valid"])

    def test_since_last_meeting_not_invented(self):
        obj = self.example(); obj["since_last_meeting"] = [{"date": "2026-11-01", "description": "event", "source_url": "https://example.invalid/news"}]
        with self.assertRaises(ValueError):
            brief.validate_brief(obj)

    def test_contact_fields_and_nonfinite_amounts_rejected(self):
        obj = self.example(); obj["people"] = [{"name": "Person", "email": "private@example.invalid"}]
        with self.assertRaisesRegex(ValueError, "contact email"):
            brief.validate_brief(obj)
        obj = self.example(); obj["funding"] = {"total_usd": float("nan")}
        with self.assertRaisesRegex(ValueError, "nonfinite"):
            brief.validate_brief(obj)


class CRMCurrencyTests(unittest.TestCase):
    def normalize(self, amounts, header="Amount"):
        import csv
        import subprocess
        import sys
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        work = Path(tmp.name); source = work / "input.csv"
        with source.open("w", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(["Account Name", "Website", "Account ID", "Opportunity Name", "Stage", header, "Currency"])
            for i, (amount, currency) in enumerate(amounts):
                writer.writerow(["One", "one.invalid", "a1", f"Deal {i}", "Qualification", amount, currency])
        run = subprocess.run([sys.executable, str(ROOT / "skills/crunchbase-prospect-finder/scripts/crm_export.py"), "--input", str(source), "--out-dir", str(work / "out")], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        with (work / "out/crm-accounts.csv").open(encoding="utf-8-sig") as fh:
            row = next(csv.DictReader(fh))
        return row, json.loads((work / "out/crm-deals.json").read_text())["deals"]

    def test_mixed_currencies_preserve_original_without_sum(self):
        row, deals = self.normalize([("$100.00", "USD"), ("100", "EUR")])
        self.assertFalse(row.get("Open amount"))
        self.assertEqual(row["Open amount status"], "mixed_currencies")
        self.assertEqual([d["currency"] for d in deals], ["USD", "EUR"])
        self.assertEqual(deals[0]["amount_original"], "$100.00")
        self.assertEqual(deals[0]["currency_original"], "USD")

    def test_same_explicit_currency_complete_sum(self):
        row, _ = self.normalize([("100", "usd"), ("200", "USD")])
        self.assertEqual(row["Open amount"], "300")
        self.assertEqual(row["Open amount currency"], "USD")
        self.assertEqual(row["Open amount status"], "complete")

    def test_unknown_missing_and_converted_amounts_no_total(self):
        for amounts, header, status in [
            ([("$100", "")], "Amount", "unknown_currency"),
            ([("100", "USD"), ("", "USD")], "Amount", "missing_amount"),
            ([("100", "EUR")], "Amount (converted)", "unknown_currency")]:
            with self.subTest(status=status, header=header):
                row, _ = self.normalize(amounts, header)
                self.assertFalse(row.get("Open amount"))
                self.assertEqual(row["Open amount status"], status)

    def test_five_bundled_copies_identical(self):
        paths = list((ROOT / "skills").glob("*/scripts/crm_export.py"))
        self.assertEqual(len(paths), 5)
        self.assertEqual(len({p.read_bytes() for p in paths}), 1)


if __name__ == "__main__":
    unittest.main()
