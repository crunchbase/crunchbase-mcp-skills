# Workflow: Saved-List Event Monitoring

Goal: review timestamped events and current state for a user-selected, persistent company list. Do not claim historical field changes without a comparable prior snapshot.

## First use

If the user explicitly asks to create or save a company list for monitoring, resolve the proposed companies, preview the canonical linked set and list name, then follow `saved-lists.md`. Record a monitoring baseline date separately from list creation and membership version.

If the user asks only to monitor companies or review an existing list, do not create or change a list automatically.

## Later reviews

1. Query saved lists and resolve the exact list selected by the user.
2. Use a review baseline from the user's date or the relevant prior task record. If the user requests changes or events over time and no baseline is established, ask for the period before retrieving those events; offer a concrete period for acceptance. A request for current state alone needs no historical baseline. Do not silently substitute current state for a requested change report.
3. Resolve every predicate and order field through `cb_reference`.
4. Query organizations with `identifier in_list [<list_id>]`, requesting canonical identifiers, funding summary fields, dated leadership and layoff fields, employee band, current status, facets, and 30/90-day trend scores.
5. For a requested review of events over time, query `funding_rounds` with `funded_organization_identifier in_list [<list_id>]` and an announcement-date predicate for the agreed review window. Paginate to completeness. A current-state-only request does not require this historical query.
6. Query `acquisitions` with `acquiree_identifier in_list [<list_id>]`, ordered by announcement date, when needed for the requested event review or to establish present pipeline state. Use the agreed window for event comparisons; include earlier acquisitions when present state requires them.
7. Retrieve an entity profile only for an event that needs additional detail, using explicit fields and selected cards.

## Interpretation boundaries

- Funding, leadership, layoff, and acquisition fields with dates can be compared with the review baseline.
- A 30-day or 90-day trend score describes its own built-in window; do not present it as change since another baseline.
- Status and employee band are current state unless a prior snapshot supplied in the task proves a difference.
- Saved-list membership does not preserve historical organization fields.
- A financing event should prompt review of prior sourcing history and disposition; do not label it a sourcing failure without that context.

## Membership updates

Add, replace, or version membership only when explicitly requested. Resolve every new entity, preview the delta, and follow the reconciliation procedure in `saved-lists.md`.

## Output

| Company | Dated event or current state | Detail | Suggested review action |
|---|---|---|---|

Then include:

- **Tracked universe:** list name, list ID, member count, and membership version; include a baseline date for a time-based review
- **Events since baseline:** for a requested time-based review, funding, leadership, layoffs, and acquisitions supported by event dates
- **Current-state review:** status, employee band, facets, and built-in trend windows
- **Members with no dated event in the returned results:** for a time-based review, collapsed into one concise line
- **Source notes:** use `—` conventions from `output-contract.md`
