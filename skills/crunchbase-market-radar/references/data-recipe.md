# Structured market retrieval and normalization

Read query-core before constructing searches. Collection names below identify capabilities, not permission to copy a static predicate. Resolve current field contracts and actual identifiers. Avoid expert aggregation tools.

## Retrieve the agreed universe

1. Resolve the industry with category autocomplete; ask if credible meanings remain. Discover micro-industries through `micro_categories` using its live `categories` relationship, or resolve the user's named micro-industries. Retrieve all pages of the agreed segment set. A bounded segment comparison is acceptable only when explicitly agreed and labeled as such.
2. Search `organizations` with the agreed industry, geography, size, stage, and micro-industry filters. Keep the same filters for every denominator. Request identifier, website, `micro_categories`, `founded_on`, and `growth_prediction_tier`. `funding_prediction_tier` is optional. Request only available output fields; absence is unknown, not proof of an entitlement cause. Follow all pages and deduplicate UUIDs.
3. Retrieve `funding_rounds` for the resolved organization identifiers in batches, with explicit `funded_organization_identifier`, `announced_on`, `investment_type`, and `money_raised` fields. Resolve predicates on organization identity and dates. Fetch both adjacent twelve-month windows, ending on the as-of date. For November 5, 2026 these are November 6, 2025–November 5, 2026 and November 6, 2024–November 5, 2025. Keep any agreed funding-type filters consistent. Count distinct round UUIDs, not organizations funded.
4. Optional `market_insights`: retrieve `subject`, `direction`, `generated_on`, and identifier for the agreed segment identifiers. This is a separately attributed second opinion, not an input to labels. Preserve all pages of histories used to choose the latest observation. Do not infer a call from an empty record.
5. For a user account book, resolve named organizations first, preserve canonical IDs and all memberships, and include `account_uuids`. If the requested universe is only the account book, label the result as book-specific. A broader market comparison requires agreed scope. CRM exports supply names/domains/IDs; they are not evidence for growth or funding. Ambiguous rows stay outside calculations and are disclosed, not silently selected.

An aggregate `count` is useful for completeness but does not replace records needed for deduplication, cross-segment membership, unknown denominators, or money calculations. Record per-batch counts, reconcile unique records, and set `reported_count` to the deduplicated expected union; never add overlapping query counts. If that union is not established, coverage is incomplete.

## Normalized input

The helper consumes JSON, not raw MCP envelopes. Normalize returned fields while retaining source records separately. Dates must be full ISO dates; partial founding dates stay null unless the source establishes the exact day. Money is the returned numeric USD conversion or null, never the raw amount in another currency. Zero is a known amount. Do not invent dates, amounts, prediction labels, or UUIDs.

```json
{
  "schema_version": "crunchbase-gtm-radar/1",
  "as_of": "2026-11-05",
  "scope": {"market": "confirmed market", "geography": "confirmed geography", "funding_types": "all", "selection": "all agreed segments"},
  "coverage": {
    "segments": {"complete": true, "reported_count": 1},
    "organizations": {"complete": true, "reported_count": 1},
    "rounds": {"complete": true, "reported_count": 0}
  },
  "segments": [{"uuid": "returned-segment-uuid", "name": "Returned segment", "url": null}],
  "organizations": [{"uuid": "returned-company-uuid", "name": "Returned company", "url": "returned canonical profile URL", "segment_ids": ["returned-segment-uuid"], "founded_on": null, "growth_tier": null, "funding_tier": null}],
  "rounds": [],
  "insights": [],
  "account_uuids": [],
  "territory_policy": "memberships",
  "watch_segment_uuids": ["returned-segment-uuid"]
}
```

This deliberately small example yields insufficient comparable segments, not fabricated direction labels. A round row has `uuid`, `organization_uuid`, `announced_on`, and `money_raised_usd`. An optional insight row has `segment_uuid`, `direction` (the returned enum), `generated_on`, and source `url`. Schema supports current direction enums `c100_growing`, `c200_stable`, `c300_declining`; an unfamiliar live enum requires a tested adapter update, not guessed mapping.

For an explicit request to split a book into exclusive territories, propose `territory_policy: "balanced-v1"` and obtain acceptance unless already specified. This deterministically chooses the largest remaining segment with at most 40% of classified accounts where possible (otherwise the largest), assigns matching unassigned accounts to it, and repeats up to ten territories. Canonical segment UUID breaks ties; remaining accounts are Other. This is a transparent heuristic, not a guarantee of equal workloads. Default `memberships` retains all overlapping assignments. The account set and chosen policy are part of the monitoring fingerprint.

The helper validates complete retrieval and conflicting duplicates, rejects future observed dates and malformed money, and excludes segments lacking observed growth/founding data from peer calculations. It requires at least three sufficiently sized, fully observed peers. Optional funding predictions affect ranking only if observed for every organization in every eligible peer; otherwise they remain descriptive values.

Run `python scripts/radar.py score --input radar-input.json --out-dir market-radar-out`. Exit 0 means a comparison was produced; exit 2 means insufficient comparable segments (files explain why); exit 1 means invalid input or an execution error. Do not claim success from the existence of an output directory left by a previous run. Use a distinct output directory per run.
