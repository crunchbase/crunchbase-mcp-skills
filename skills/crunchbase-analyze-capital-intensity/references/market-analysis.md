# Workflow: Capital Intensity Within a Confirmed Universe

Goal: analyze company count, capital deployment, round-size trends, concentration, stage mix, and formation within a user-confirmed company universe. Use the result to inform market timing without claiming a whole-market census.

## Establish the universe

This is a stop gate. If no universe below has been supplied or explicitly confirmed, ask the user to choose one before calling any Crunchbase tool. Do not build, test, or analyze a proxy universe in the same turn.

Use one of:

- Company names or domains supplied by the user
- An existing saved Crunchbase list selected by the user
- A candidate set produced by a landscape and explicitly confirmed by the user

Resolve and show canonical linked organizations before analysis. State the inclusion rule, adjacent exclusions, geography or stage constraints, and confirmed denominator. A one-off analysis does not require a saved-list write.

If the supplied universe repeats the same exact name, domain, permalink, or resolved UUID, deduplicate it and proceed with the unique denominator. Do not ask whether an exact repeat was intended to represent a different company.

Before analytical retrieval, reuse the time period, comparison, and capital definition already supplied or agreed. Ask one concise question about any missing choice that materially affects the analysis. A trailing 24-month window comparing the latest 12 months with the prior 12 is an option to propose, not a silent default. Confirm whether capital means all funding rounds or equity-only when that distinction is material; use a proposed definition only after the user accepts it.

## Retrieve the evidence

1. For a saved list, keep this market-analysis workflow primary and use live-confirmed `in_list` predicates directly on organization and funding-round searches. Load `saved-lists.md` only for list lookup and membership; do not route the analysis through pipeline monitoring.
2. For an unsaved universe, use confirmed organization permalinks with the live-supported multi-identifier operator.
3. Query organization fields needed for the census and formation buckets.
4. Query all funding rounds across the agreed absolute date boundaries, ordered by announcement date and paginated to the returned count. Include both periods when a comparison was requested.
5. Apply the agreed capital definition, including the live-confirmed equity predicate for equity-only capital, and state it in the deliverable.
6. Obtain organization profile URLs for all companies shown in round tables.

The date-bounded `cb_search_query` is required even when organization profiles return funding-round cards. Do not substitute profile cards for the count-audited round search or replace the user's dates with a 24-month window.

## Calculate

Use the definitions in `calculation-spec.md` over the agreed period boundaries for:

- Round counts for the requested period and any agreed comparison
- Numeric capital totals and `—` amount counts
- Median numeric round size
- Funding-type mix
- Top-three capital concentration
- Formation by year within the confirmed universe

The `scripts/derive_metrics.py` capital-window output implements the standard trailing 24-month / 12-versus-12 comparison only. Use it for that comparison when agreed. For other periods, calculate the same aggregates directly over the specified boundaries; do not feed a custom-window dataset into the helper and report its fixed-window output as the requested analysis.

Show three to five largest numeric rounds in the agreed window with lead investors.

## Interpret

Describe evidence that supports both greater and lower capital intensity. Give a conditional conclusion with a confidence level and the strongest counterinterpretation. Frame the practical question as whether the user's mandate still supports taking meetings within this universe.

## Output

- **Confirmed universe:** definition, denominator, and unresolved inputs
- **Headline metrics:** timeframes and amount-count denominators
- **Period comparison:** the agreed periods, when requested
- **Concentration and stage mix**
- **Formation within the confirmed universe**
- **Notable rounds:** linked companies, round type, amount, date, leads
- **Conditional interpretation:** evidence, confidence, and counterinterpretation
- **Questions for follow-up**

Keep the analysis read-only. If the user also explicitly requests saving or updating the universe, hand that operation to `crunchbase-manage-saved-lists` as a separate workflow, carrying forward the canonical membership and existing authorization. Do not require the user to authorize the same operation again; list preview and persisted-membership verification belong to that workflow.
