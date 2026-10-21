# Calculation Specification

Use these definitions for recency, market, and monitoring metrics. The optional `scripts/derive_metrics.py` helper implements the same rules.

## Run the local helper

Requires Python 3.9 or later; standard library only. From this installed skill directory, run `python3 scripts/derive_metrics.py input.json > metrics.json` (or pipe JSON to the same script without a filename). Paths are relative to this skill, not the repository.

Example normalized input:

```json
{"as_of":"2026-09-30","rounds":[{"uuid":"round-1","announced_on":"2026-09-10","money_raised_usd":1000000,"investment_type":"seed","company_uuid":"company-1"}],"organizations":[{"uuid":"company-1","founded_on":"2020-01-01","last_funding_at":"2026-09-10"}]}
```

Map returned identifiers to `uuid`; map `money_raised.value_usd` to `money_raised_usd`. Never substitute raw foreign-currency `value` when `value_usd` is missing. Preserve explicit zero; encode missing values as JSON `null`, not the display dash. Unwrap a returned date object's `value` and retain its `precision` in the evidence notes. Do not manufacture day precision: calculate year-only formation buckets separately when needed, and exclude imprecise dates from day-sensitive calculations unless their placement is unambiguous.

Validate dates before invoking the helper. Exclude and report invalid or future events; omit an invalid round from the calculation, or set an invalid organization date to `null` while retaining the organization in the confirmed universe. Keep excluded-date counts separate from originally missing dates. The helper emits JSON on success; malformed inputs exit with status 2 and an `error:` message on stderr. Correct only evidenced normalization mistakes, then rerun once; otherwise report the unsupported calculation. Never present stale output from a failed invocation.

The helper supports only the fixed trailing windows below. For a custom period, calculate directly from the normalized records under the user's exact boundaries. Inspect numeric-value counts before rendering totals: all-unknown amounts remain unknown even when an empty sum is zero.

## General rules

- Fix one `as_of` date at the start of the task in the user's timezone.
- Deduplicate organizations and rounds by UUID before calculating.
- Use `value_usd` for money calculations.
- Exclude `—` amounts from sums, medians, and concentration calculations; count those rounds separately.
- Reject future event dates from calculations and surface them for review.
- Keep raw retrieved values separate from derived labels.

## Full months since an event

For event date `E` and as-of date `D`:

`months = ((D.year - E.year) * 12 + (D.month - E.month)) - (1 if D.day < E.day else 0)`

Do not divide elapsed days by 30.

Funding-recency labels:

- Fewer than 12 full months: `recent`
- 12 through 17 full months: `intermediate`
- 18 or more full months: `extended interval`
- No returned event date: `—`

These labels describe timing only. They do not establish fundraising intent, company health, or outreach priority.

## Trailing capital windows

Use the time window and comparison requested or accepted by the user. The helper supports the following fixed comparison; use its output only when this comparison is agreed.

Using calendar-month subtraction:

- Current period: `[D minus 12 months, D]`
- Prior period: `[D minus 24 months, D minus 12 months)`

For other requested periods, apply the same aggregate definitions below to the user's date boundaries using a separate calculation. Do not substitute the helper's fixed 24-month output for the requested period.

For each period report:

- Total round count
- Rounds with a numeric USD amount
- Rounds shown as `—`
- Total disclosed USD capital
- Median numeric round size
- Funding-type mix by count

When the prior value is zero, show percent change as `n/a` rather than dividing by zero.

## Concentration

Calculate top-three concentration over the agreed window as the sum of the three largest numeric round amounts divided by total numeric capital in that window. The helper calculates this over its fixed trailing 24-month window; use that result only when this is the agreed window. Report `n/a` when total numeric capital is zero.

## Formation

Bucket confirmed organizations by the year component of `founded_on`. Include dates on or before `as_of`; reject later founding dates for review. Omit organizations with no founding date from these buckets. Label the result “formation within the confirmed universe.” Do not extrapolate it to the whole market.

For formation percentages, divide each year bucket by the number of organizations with valid founding dates on or before `as_of`. Separately report coverage as that valid-date count divided by the entire deduplicated confirmed universe, including missing or excluded dates. For example, two valid dates in a three-company universe give 2/3 coverage; one company in each year gives 50% per year, not 33%. With no valid dates, year shares are `n/a`.
