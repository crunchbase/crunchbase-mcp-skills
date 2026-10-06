#!/usr/bin/env python3
"""Deterministic calculations for Crunchbase sourcing workflows.

Input JSON:
{
  "as_of": "YYYY-MM-DD",
  "rounds": [
    {
      "uuid": "...",
      "announced_on": "YYYY-MM-DD",
      "money_raised_usd": 1000000 | null,
      "investment_type": "seed" | null,
      "company_uuid": "..."
    }
  ],
  "organizations": [
    {
      "uuid": "...",
      "founded_on": "YYYY-MM-DD" | null,
      "last_funding_at": "YYYY-MM-DD" | null
    }
  ]
}
"""

from __future__ import annotations

import argparse
import calendar
import json
import math
import statistics
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any


def parse_date(value: str, label: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be an ISO date (YYYY-MM-DD): {value!r}") from exc


def subtract_months(value: date, months: int) -> date:
    if months < 0:
        raise ValueError("months must be non-negative")
    month_index = value.year * 12 + value.month - 1 - months
    year, zero_based_month = divmod(month_index, 12)
    month = zero_based_month + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def full_months_since(event_date: date, as_of: date) -> int:
    if event_date > as_of:
        raise ValueError(f"event date {event_date} is after as_of {as_of}")
    months = (as_of.year - event_date.year) * 12 + as_of.month - event_date.month
    if as_of.day < event_date.day:
        months -= 1
    return months


def recency_label(months: int | None) -> str:
    if months is None:
        return "—"
    if months < 12:
        return "recent"
    if months < 18:
        return "intermediate"
    return "extended interval"


def require_rows(value: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be an array")
    for index, row in enumerate(value):
        if not isinstance(row, dict):
            raise ValueError(f"{label}[{index}] must be an object")
    return value


def dedupe_by_uuid(rows: list[dict[str, Any]], label: str) -> list[dict[str, Any]]:
    seen: set[str] = set()
    output: list[dict[str, Any]] = []
    for row in rows:
        row_id = row.get("uuid")
        if not isinstance(row_id, str) or not row_id:
            raise ValueError(f"every {label} row requires a non-empty uuid")
        if row_id in seen:
            continue
        seen.add(row_id)
        output.append(row)
    return output


def numeric_amount(value: Any) -> float | int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"money_raised_usd must be numeric or null: {value!r}")
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"money_raised_usd must be finite and non-negative: {value!r}")
    return value


def investment_type_label(value: Any) -> str:
    if value is None or value == "":
        return "—"
    if not isinstance(value, str):
        raise ValueError(f"investment_type must be a string or null: {value!r}")
    return value


def period_metrics(rounds: list[dict[str, Any]]) -> dict[str, Any]:
    amounts = [numeric_amount(row.get("money_raised_usd")) for row in rounds]
    numeric = [amount for amount in amounts if amount is not None]
    stage_mix = Counter(investment_type_label(row.get("investment_type")) for row in rounds)
    return {
        "round_count": len(rounds),
        "numeric_amount_count": len(numeric),
        "dash_amount_count": len(rounds) - len(numeric),
        "capital_usd": sum(numeric) if numeric or not rounds else None,
        "median_round_usd": statistics.median(numeric) if numeric else None,
        "stage_mix": dict(sorted(stage_mix.items())),
    }


def derive_metrics(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("input must be a JSON object")
    as_of = parse_date(payload.get("as_of"), "as_of")
    rounds = dedupe_by_uuid(require_rows(payload.get("rounds", []), "rounds"), "round")
    organizations = dedupe_by_uuid(
        require_rows(payload.get("organizations", []), "organizations"), "organization"
    )

    cutoff_12 = subtract_months(as_of, 12)
    cutoff_24 = subtract_months(as_of, 24)
    current: list[dict[str, Any]] = []
    prior: list[dict[str, Any]] = []
    window_rounds: list[dict[str, Any]] = []

    for row in rounds:
        announced = parse_date(row.get("announced_on"), f"round {row['uuid']} announced_on")
        if announced > as_of:
            raise ValueError(f"round {row['uuid']} has a future announced_on date")
        if cutoff_12 <= announced <= as_of:
            current.append(row)
            window_rounds.append(row)
        elif cutoff_24 <= announced < cutoff_12:
            prior.append(row)
            window_rounds.append(row)

    numeric_window = [
        numeric_amount(row.get("money_raised_usd")) for row in window_rounds
    ]
    numeric_window = [amount for amount in numeric_window if amount is not None]
    total_window = sum(numeric_window)
    top_three = sum(sorted(numeric_window, reverse=True)[:3])
    concentration = top_three / total_window if total_window else None

    formation = Counter()
    organization_recency = []
    for row in organizations:
        founded = row.get("founded_on")
        if founded:
            founded_date = parse_date(founded, f"organization {row['uuid']} founded_on")
            if founded_date > as_of:
                raise ValueError(f"organization {row['uuid']} has a future founded_on date")
            formation[founded_date.year] += 1
        last_funding = row.get("last_funding_at")
        months = None
        if last_funding:
            months = full_months_since(
                parse_date(last_funding, f"organization {row['uuid']} last_funding_at"),
                as_of,
            )
        organization_recency.append(
            {"uuid": row["uuid"], "full_months_since": months, "label": recency_label(months)}
        )

    notable = sorted(
        (
            {
                "uuid": row["uuid"],
                "company_uuid": row.get("company_uuid"),
                "announced_on": row["announced_on"],
                "investment_type": investment_type_label(row.get("investment_type")),
                "money_raised_usd": numeric_amount(row.get("money_raised_usd")),
            }
            for row in window_rounds
            if row.get("money_raised_usd") is not None
        ),
        key=lambda row: (-row["money_raised_usd"], row["announced_on"], row["uuid"]),
    )[:5]

    return {
        "as_of": as_of.isoformat(),
        "window_boundaries": {
            "current_start_inclusive": cutoff_12.isoformat(),
            "prior_start_inclusive": cutoff_24.isoformat(),
            "prior_end_exclusive": cutoff_12.isoformat(),
        },
        "current_12_months": period_metrics(current),
        "prior_12_months": period_metrics(prior),
        "top_three_capital_concentration": concentration,
        "formation_within_confirmed_universe": {
            str(year): formation[year] for year in sorted(formation)
        },
        "organization_recency": sorted(organization_recency, key=lambda row: row["uuid"]),
        "notable_rounds": notable,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", help="Input JSON file; omit to read stdin")
    args = parser.parse_args()
    try:
        raw = Path(args.input).read_text() if args.input else sys.stdin.read()
        payload = json.loads(raw)
        result = derive_metrics(payload)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
