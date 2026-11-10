# Direction rule version 1

The deterministic rule preserves the incoming GTM thresholds. It is a descriptive heuristic, not a calibrated probability, statistical significance test, or evidence of purchasing intent.

For each segment, N is its organization count, VL its very-likely-growth count, Y its count founded in the last 36 months, Rc/Rp its current/prior twelve-month round counts. N must be at least 15, Rc+Rp at least 12, and Rp at least 5. Every member needs observed growth tier and full founding date; otherwise the segment is insufficient evidence. At least three eligible segments are needed.

Compute deal change `Rc/Rp - 1` and its median among eligible peers. Relative change is the difference from that median. Expected current rounds are `Rp * (1 + median change)` and z is `(Rc - expected)/sqrt(expected)`, or zero when expected is zero. Compare VL/N and Y/N to their peer medians. Preserve the original zero-median convention: ratio is one when both values are zero and two when the numerator is positive and median zero; disclose this convention when explaining the rule.

First matching rule wins:

| Rule | Label | Condition |
| --- | --- | --- |
| D1 | declining | Relative change ≤ -0.20 and z ≤ -1.5 |
| D2 | declining | Relative change ≤ -0.10, z ≤ -1, growth-share ratio < 1 |
| E1 | emerging | Youth-share ratio ≥ 1.5, relative change ≥ 0, Y ≥ 5 |
| G1 | growing | Relative change ≥ 0.10 and z ≥ 1 |
| G2 | growing | Relative change ≥ 0 and growth-share ratio ≥ 1.25 |
| S1 | steady | Otherwise |

Within label groups order by `relative change + (growth share - peer median) + 0.5*(youth share - peer median)`. Add `0.5*(predicted-raise share - peer median)` only when every eligible peer has complete funding-prediction data. Canonical UUID breaks ties. Emerging/growing precede steady, then declining, then unclassified.

Focus candidates are the first three emerging/growing segments. Reconsider candidates are the three weakest declining segments unless growth ratio ≥ 1.25 or youth ratio ≥ 1.5. These are conditional investigation recommendations, not instructions to allocate or cut budget. Money is reported with known/unknown amount counts and never affects labels. Overlapping memberships mean totals cannot be summed across segments. Crunchbase market insights never alter computed labels; show disagreements explicitly.
