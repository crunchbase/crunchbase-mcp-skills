# Calculation Specification

Use these definitions for recency, market, and monitoring metrics. The optional `scripts/derive_metrics.py` helper implements the same rules.

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
