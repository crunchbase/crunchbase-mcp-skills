# Funding Round Search

Search `funding_rounds` directly for recent activity, funding histories, and capital calculations.

## Query patterns

Resolve each predicate and order field through `cb_reference`. Candidate fields commonly include:

- `identifier`, `announced_on`, `closed_on`, `investment_type`, `investment_stage`
- `money_raised`, `is_equity`, `post_money_valuation`
- `funded_organization_identifier`, `funded_organization_categories`
- `funded_organization_description`, `funded_organization_location`
- `funded_organization_funding_total`, `lead_investor_identifiers`, `investor_identifiers`

Use:

- `funded_organization_identifier in_list [<list_id>]` for a saved company list.
- The live-supported multi-identifier operator with organization **permalinks** for a confirmed unsaved universe.
- `announced_on` with absolute dates for recency windows.
- Live-confirmed funding-type enum values for stage filters.
- `is_equity eq true` only when the requested capital definition excludes all rounds that are not equity-only.

Do not pass organization UUIDs to an identifier operator whose field-detail example uses permalinks.

## Full funding histories

A company's `last_funding_*` fields are a summary, not a history. Before interpreting financing trajectory, query all funding rounds for the canonical organization, sort by announcement date, and paginate to the returned count.

Always pair an amount with its round type and announcement date. Count rounds whose amount is `—` separately from rounds included in capital and median calculations.

## Company links

Funding-round results expose the funded organization identifier, but the row's top-level URL is the funding-round profile. Batch-search the corresponding organizations and use their top-level URLs for company links. Keep the round URL only when linking the transaction itself.
