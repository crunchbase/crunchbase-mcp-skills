# Ranking Formula — pulse/v2

`scripts/pulse.py rank` computes it; this page is the human-readable copy. When a user asks how the list is ranked, explain it in these plain terms (no code, no field names).

**Score = signal points + momentum points + tier bonus + focus bonus - layoff penalty**

## Signal points

For each kind of signal, the best event counts in full and each further event of the same kind adds 3 points (at most 9).

Event points = weight x strength x freshness

| Signal | Weight | Strength |
|---|---|---|
| New money raised | 40 | equity round or (for an investor) a fund close 1.0; debt or convertible note 0.6; grant or crowdfunding 0.4; secondary sale 0 (not new money) |
| Leadership change | 30 | C-level, president, founder or general counsel 1.0; VP, head of, managing director 0.8; other 0.5; a departure counts 0.6 of that |
| Newly predicted to raise within 0-5 months | 25 | 1.0 |
| Already predicted to raise within 0-5 months | 10 | flat, no freshness decay |
| New office | 20 | 1.0 |
| Product launch | 15 | 1.0 |
| Newly predicted to be acquired (newest Very Likely after a previous positive reading, not previously confirmed) | 20 | 1.0 |
| Growth insight (customer, headcount, operations, market-share, usage or financial growth), dated by its newest article | 15 | 1.0 |
| Partnership (only when tracked) | 10 | 1.0 |

Freshness halves every 30 days: 1.0 today, 0.5 at 30 days, 0.25 at 60 days, 0.125 at 90 days.

A prediction counts only when it is Very Likely or Probable with 0-5 months as the most likely window, and was made after the company's latest new-money round. It is "newly" predicted only when an earlier prediction in the last 180 days was not; with no earlier prediction to compare, it counts as already predicted.

## Momentum points (-5 to 20)

- Crunchbase growth score divided by 10 (0-10)
- Change in heat score (media and market attention) over 90 days divided by 4, capped at -5 and +5
- Crunchbase predicts growth: Very Likely +5, Probable +3

## Bonuses and penalty

- Tier A +10, Tier B +5 (when the book has tiers)
- Focus +8 when an event in the window mentions a word from "what we sell" (for example "fraud", "compliance")
- Layoffs: -15 x freshness for each layoff report in the window

## List rules

- Only accounts with a sourced signal in the window enter the displayed signal list; do not fill it with momentum-only accounts.
- Ties: most recent signal first, then normalized display name and canonical UUID.
- Same inputs always give the same order.

## Example

A Series B announced 12 days ago at a Tier A account with growth score 80 and heat up 8 points: 40 x 1.0 x 0.76 = 30.3 signal, plus 8 + 2 = 10 momentum, plus 10 tier = 50.3.

## Evidence eligibility

A score requires complete reconciled retrieval for the selected signals and layoff penalty, plus valid growth_score (0..100), heat_score_delta_d90 (-100..100) and a recognized growth prediction tier. Unknown required momentum factors produce null score/rank and insufficient_evidence, not zero or silently rescaled weights. Known numeric zero remains valid. The signal rows may still be useful as unranked evidence. Partial collection coverage similarly makes all scores unscored and blocks state commit.

Reject future/undated occurred events, unsourced observations and nonfinite/out-of-range values. Secondary and post-IPO secondary sales are not new money. Missing prediction history cannot establish a new transition. Counts refer to deduplicated records; equal-date conflicting prediction readings use conservative deterministic selection. Preserve the formula's original weights as a review-priority heuristic, not calibrated purchasing probability.

## Inclusive calendar windows

An N-day event or play window ending on the as-of date includes both endpoints: start = as-of − (N − 1) calendar days. Thus 60 days ending November 5, 2026 starts September 7, and a one-day window contains only November 5. Fetch using these exact boundaries; play windows are capped at the accepted event lookback. Explicit `--since` is a change-detection boundary, not an N-day event-window substitute.

All computed scores and individual components, including layoff penalties, require `pulse.py`, even in an unranked review. Without execution, report only raw evidence counts and limitations; do not describe a zero penalty as calculated.

Scope fingerprints now include `window_policy: inclusive-calendar-days/v1`. Earlier state is intentionally incompatible: preserve it, establish a newly authorized baseline at a new path, and do not compare or alert across that policy change. Formula weights and rubric version are unchanged.
