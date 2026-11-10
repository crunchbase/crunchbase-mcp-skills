# Account Pulse retrieval and runtime contract

Read `query-core.md` and `entity-resolution.md` before queries. Collection and field names here are discovery hints: live metadata decides predicate operators, values and identifier forms. No expert tool other than entity resolution is allowed.

## Inputs and normalization

Run `python scripts/pulse.py book <accounts.csv> --out book.json` (paths relative to this skill directory for scripts). A supplied CRM export uses `crm-export.md` first. The book parser retains names, supplied domains/permalinks and existing tiers. It does not establish identity. Resolve every named account with the resolver; domain-only structured search is the bounded fallback described in entity-resolution.md. A named saved list is read using cb_list_query/cb_list_get, with ambiguous names clarified and every page retrieved. This workflow never changes lists.

Fetch confirmed organization fields needed for ranking: identifier, website_url, growth_score, heat_score_delta_d90, growth_prediction_tier, latest financing date/type, and optional description/employee fields. Pass normalized records through `pulse.py match --book book.json --orgs organizations.json --resolved resolved.json --out accounts.json`. The optional resolver map maps original names to confirmed permalinks; it is not a guess table. `match` accepts exact canonical identity or a unique exact supplied domain; multiple domain candidates and name-only rows remain unresolved.

`accounts.json` contains `schema_version: "pulse-accounts/v1"`, `accounts` with required uuid, permalink, name, url and optional tier/profile fields, plus unresolved/ambiguous records and requested/confirmed counts. Canonical handoffs from other GTM workflows may supply those same account records. Normalize fields explicitly and preserve their provenance; do not infer missing momentum values.

## Retrieval

Batch confirmed account identifiers using supported query operators. Request all pages while reported total exceeds retrieved unique records; deduplicate by UUID. Detect repeated cursors/no progress, stop, and disclose incompleteness rather than loop. A returned count of 301 with 300 rows requires another page. Separate prediction-history windows from event lookback and retain the baseline needed for a transition.

| Signal | Collection hint | Organization/date hints |
| --- | --- | --- |
| Funding | funding_rounds | funded_organization_identifier, announced_on, investment_type, money_raised |
| Investor fund records | funds | owner_identifier, started_on, money_raised; mark account is_investor=true |
| Leadership | key_employee_changes | organization_identifier, key_event_date, description, press_reference_link |
| Layoff penalty (required) | layoffs | organization_identifier, key_event_date, description, press_reference_link |
| Product | product_launches | organization, key_event_date, description, press_reference_link |
| Office | addresses | organization, opening_date, opening_press_reference_link |
| Partnership | partnership_announcements | organization, key_event_date, description, press_reference_link |
| Funding prediction | funding_predictions | organization, generated_on, probability_tier, probability_score_timeseries, reasons |
| Acquisition prediction | acquisition_predictions | organization, generated_on, probability_tier |
| Growth insight | growth_insights | organization, generated_on, growth_indicators, press_references |

Predictions use the agreed history interval (propose 180 days), retaining previous distinct readings. Person/product queries are optional enrichment for shown accounts; a missing optional person is not a failed signal search. A required signal unavailable from the connector leaves the requested ranking incomplete; propose a narrower signal scope rather than silently dropping it. No metadata absence is proof of a subscription-plan cause.

Retain raw search responses as JSON with their collection_id and entities. The adapter accepts flat projected rows, nested properties objects, and field_id/value property arrays without changing values. Conflicting duplicate properties fail. Supported tool wrappers include structuredContent/content text and data envelopes. The helper rejects error payloads. Compact records are an explicit normalization alternative, not permission to fabricate evidence:

- Events: `{kind: "funding"|"fund"|"leadership"|"launch"|"office"|"partnership"|"layoff"|"growth", id, org: <permalink>, date: YYYY-MM-DD, source: <URL>, created: <optional record date>, desc}`. Funding adds round and amount_usd; growth adds kinds and a dated source article. Unknown amount is null. A funding source may be its returned Crunchbase round URL.
- Predictions: `{kind: "prediction"|"acq_prediction", id, org, generated_on, tier, score: <optional 0..1>, ts: {months_00_to_05: <0..1>, ...}, reasons: []}`. Preserve provider values and unknowns. A prediction horizon is not an occurred event.
- People: `{kind: "person", org, name, title, url, linkedin}` from confirmed public records, no email/phone.

Future/undated occurred events, invalid numbers and unsourced observations are rejected and disclosed. An event's creation date cannot replace its occurrence/announcement date. Growth summary dates cannot replace underlying article dates. Sources are retained; the agent must still judge grounding against actual records.

## Coverage manifest and execution

Write coverage from actual query results, not expected counts:

```json
{"schema_version":"pulse-coverage/v1","as_of":"2026-11-05","accounts":{"requested":1,"confirmed":1},"collections":{"funding_rounds":{"retrieved":1,"total":1,"complete":true},"layoffs":{"retrieved":0,"total":0,"complete":true}}}
```

Collections must include every selected signal plus layoffs, and funds when funding monitors an investor account. Counts are unique input records before valid-event filtering, summed only over disjoint query batches. Complete is true only after all pages reconcile with reported totals. Optional enrichment collections included in the manifest must also reconcile. Missing totals stay null/incomplete. Account unresolved counts must remain visible. A partial run can return evidence with null scores but cannot commit state.

```sh
python scripts/pulse.py rank --accounts accounts.json --data events.json --coverage coverage.json --today 2026-11-05 --signals funding --lookback 90 --out pulse-result.json --list-csv pulse-ranked.csv
```

Pass accepted `--focus`, `--buyer-titles`, `--plays-window`, `--plays-scope`, `--alert-scope`, and `--top` when relevant. Add `--feed-dir` for machine-readable predicted-raise feeds (`--feed-all` includes ongoing predictions). `--since` supplies an explicit date window without pretending there was a previous snapshot. Read `scheduled-task.md` before `--state`/`--write-state`.

Result schema is `pulse-result/v2`: as_of, scope (canonical UUID book, tiers, signals, rubric), coverage, complete, coverage_issues, rejected_observations, ranked, call_list, plays, raise_feed, alerts, needs, baseline, state_written and stats. Ranked rows preserve UUID, permalink, source signals, score/status/rank. Feed JSON is `pulse-feed/v2`; ranked CSV rows use `pulse-ranked/v2` and include schema_version/as_of/UUID. Blank CSV numeric cells mean unknown, not zero. JSON output carries scope/coverage for the CSV. `needs` may suggest people or prediction reasons; fetch at most one applicable enrichment batch or disclose absence. Do not loop to populate every optional field.

A funds search started_on value dates the fund record/start; it does not prove a close. Raw funds rows retain fund_start with no new-money points. A confirmed close may enter compact kind fund only from separately returned dated closure evidence (for example a supported announced-on card with corroborating source). Never relabel started_on as a close to fill a missing date.

## Inclusive calendar windows

An N-day event or play window ending on the as-of date includes both endpoints: start = as-of − (N − 1) calendar days. Thus 60 days ending November 5, 2026 starts September 7, and a one-day window contains only November 5. Fetch using these exact boundaries; play windows are capped at the accepted event lookback. Explicit `--since` is a change-detection boundary, not an N-day event-window substitute.

All computed scores and individual components, including layoff penalties, require `pulse.py`, even in an unranked review. Without execution, report only raw evidence counts and limitations; do not describe a zero penalty as calculated.

Scope fingerprints now include `window_policy: inclusive-calendar-days/v1`. Earlier state is intentionally incompatible: preserve it, establish a newly authorized baseline at a new path, and do not compare or alert across that policy change. Formula weights and rubric version are unchanged.
