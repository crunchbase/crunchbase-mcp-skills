# Structured Query Core

Use this reference whenever a workflow calls `cb_search_query`.

## Resolve the contract

For each search:

1. Resolve every predicate and order field once per session. Prefer one `cb_reference('entities/<entity>/fields')` call when it exposes the required field contracts.
2. Call `cb_reference('entities/<entity>/fields/<field_id>')` only for a predicate or order field whose operator, enum, identifier form, or value shape was not exposed by the collection-level response.
3. Cache successfully resolved field contracts for the session. Reuse them across queries; refresh only an affected contract rejected by a validation error, as described below.
4. Do not call `cb_reference` for projection-only output fields.
5. Copy the returned `operator_id`, enum spelling, identifier form, and value shape.
6. Treat examples in this skill as patterns, never as a substitute for a live field contract.

For a bounded first pass, resolve only fields needed for the next valid query and prioritize retrieval over optional enrichment. Efficiency targets do not override requested scope, necessary pagination, or verification of an authorized write.

A collection-level field catalog is sufficient when it exposes the required operator, enum, identifier form, and value shape. Request field detail only for contract information it does not expose.

## Build the query

- Use `predicates` for flat AND filters.
- Use `query` only when related-entity subqueries are required; never send `query` and `predicates` together.
- Request `field_ids` explicitly.
- Use absolute `YYYY-MM-DD` dates calculated from the current date.
- Use USD integer values for money predicates when confirmed by the live field contract.
- Resolve category and location identifiers with `cb_entity_autocomplete`; use returned permalinks rather than display labels.
- Remember that multiple values inside an `includes` or text `contains` predicate typically broaden that field. Confirm exact semantics in the live field contract.

## Pagination and completeness

The default row limit is not a complete dataset. When the answer depends on totals, medians, trends, membership reconciliation, or a complete universe:

1. Set an explicit limit.
2. Compare the returned `count` with rows received.
3. If more rows remain, pass the last result UUID as `after_id`.
4. Continue until all rows are retrieved or the user explicitly approves sampling. If an access, service, or user-imposed limit prevents completion, report the retrieved and reported counts and leave complete-universe calculations unfinished.
5. Deduplicate by entity UUID before calculating.

For an agreed exploratory first pass, a stated sample is acceptable. Label reviewed rows and any sample-only metrics with their denominator; never present their totals, medians, or trends as complete-universe results. Pagination is not a new search or refinement plan and is not constrained by a first-pass query-plan target.

## URLs

The top-level `url` belongs to the entity collection searched. For a `funding_rounds` search it is a round URL, not a company URL. Before rendering a company table, batch-search `organizations` using the funded-organization permalinks and map each organization UUID to its returned profile URL.

## Empty and error responses

For zero results, say: “No records matched the stated filters.” Audit one constraint at a time, beginning with resolved identifier values, then date, stage, geography, category or text, and money boundaries. Stop after identifying the first binding constraint and use no more than three diagnostic count queries. Label any relaxed-filter count as diagnostic; do not add those matches to the result or change the agreed mandate without user approval. Report which constraint changed the count and offer that change for the user to accept; do not speculate about source behavior.

For a validation error, inspect the named field or operator, refresh the affected field contract once through `cb_reference`, correct only the invalid component, and retry once. If the same validation failure recurs, stop that query and report the unresolved contract. For authentication, permission, metering, or service errors, report the tool state and do not substitute another data source.
