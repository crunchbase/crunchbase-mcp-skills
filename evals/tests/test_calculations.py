"""Independent arithmetic oracles and metamorphic properties for shipped helpers."""
import copy
from datetime import date
import importlib.util
from pathlib import Path
import random
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = sorted((ROOT / "skills").glob("*/scripts/derive_metrics.py"))
SPEC = importlib.util.spec_from_file_location("metrics", SCRIPTS[0])
METRICS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(METRICS)


def round_row(uuid, when, amount):
    return {"uuid": uuid, "announced_on": when, "money_raised_usd": amount, "investment_type": "seed", "company_uuid": "company-a"}


class CalculationTests(unittest.TestCase):
    def test_every_installable_helper_has_same_behavioral_source(self):
        self.assertEqual(len(SCRIPTS), 4)
        self.assertEqual(len({p.read_bytes() for p in SCRIPTS}), 1)

    def test_calendar_boundaries_and_unknown_amount_denominators(self):
        data = {"as_of": "2026-09-30", "rounds": [round_row("a", "2025-09-30", 10), round_row("b", "2026-09-30", None), round_row("c", "2025-09-29", 30), round_row("d", "2024-09-30", 0), round_row("old", "2024-09-29", 999)]}
        result = METRICS.derive_metrics(data)
        self.assertEqual(result["current_12_months"]["round_count"], 2)
        self.assertEqual(result["current_12_months"]["numeric_amount_count"], 1)
        self.assertEqual(result["current_12_months"]["median_round_usd"], 10)
        self.assertEqual(result["prior_12_months"]["round_count"], 2)
        self.assertEqual(result["prior_12_months"]["capital_usd"], 30)

    def test_leap_year_month_end(self):
        self.assertEqual(METRICS.subtract_months(date(2024, 2, 29), 12), date(2023, 2, 28))
        self.assertEqual(METRICS.full_months_since(date(2025, 8, 31), date(2026, 9, 30)), 12)

    def test_zero_is_observed_null_is_unknown(self):
        result = METRICS.derive_metrics({"as_of": "2026-09-30", "rounds": [round_row("a", "2026-01-01", 0), round_row("b", "2026-01-01", None)]})
        period = result["current_12_months"]
        self.assertEqual((period["capital_usd"], period["numeric_amount_count"], period["dash_amount_count"]), (0, 1, 1))
        self.assertIsNone(result["top_three_capital_concentration"])

    def test_future_dates_fail_in_each_input_location(self):
        cases = [{"rounds": [round_row("a", "2026-10-01", 5)]}, {"organizations": [{"uuid": "a", "founded_on": "2026-10-01"}]}, {"organizations": [{"uuid": "a", "last_funding_at": "2026-10-01"}]}]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ValueError):
                METRICS.derive_metrics({"as_of": "2026-09-30", **case})

    def test_malformed_amounts_cannot_corrupt_financial_totals(self):
        for value in (True, "5000000", -1, float("inf"), float("nan")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                METRICS.derive_metrics({"as_of": "2026-09-30", "rounds": [round_row("a", "2026-01-01", value)]})

    def test_permutation_duplicate_and_currency_scale_invariance(self):
        rows = [round_row(str(i), "2026-01-01", amount) for i, amount in enumerate([10, 20, 30, 40, None])]
        baseline = METRICS.derive_metrics({"as_of": "2026-09-30", "rounds": rows})
        self.assertEqual(baseline["top_three_capital_concentration"], .9)
        for seed in range(10):
            changed = copy.deepcopy(rows + rows)
            random.Random(seed).shuffle(changed)
            result = METRICS.derive_metrics({"as_of": "2026-09-30", "rounds": changed})
            self.assertEqual(result, baseline)
        scaled = [{**r, "money_raised_usd": r["money_raised_usd"] * 1000 if r["money_raised_usd"] is not None else None} for r in rows]
        result = METRICS.derive_metrics({"as_of": "2026-09-30", "rounds": scaled})
        self.assertEqual(result["top_three_capital_concentration"], .9)
        self.assertEqual(result["current_12_months"]["capital_usd"], 100000)


if __name__ == "__main__":
    unittest.main()
