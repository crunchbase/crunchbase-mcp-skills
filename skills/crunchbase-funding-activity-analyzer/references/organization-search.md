# Organization Search

Use organization searches for thesis landscapes, company screens, canonical profile links, and current-state monitoring.

## Structured screen

Resolve every required predicate and order contract through `cb_reference` unless a successful resolution is already available in the current session. Reuse valid contracts and follow `query-core.md` for a targeted refresh after a validation error. Candidate fields commonly include:

- `identifier`, `website_url`, `short_description`, `description`
- `categories`, `category_groups`, `location_identifiers`
- `funding_total`, `last_funding_at`, `last_funding_type`, `last_funding_total`
- `last_equity_funding_type`, `funding_stage`, `founded_on`
- `num_employees_enum`, `investor_identifiers`, `founder_identifiers`
- `status`, `operating_status`, `ipo_status`, `facet_ids`
- `last_key_employee_change_date`, `last_layoff_date`
- `rank_org`, `rank_delta_d30`, `rank_delta_d90`

Apply the confirmed mandate using live-confirmed enum values and operator semantics. Retain company and private-company scope. Ask for unresolved geography, stage, funding cap, or operating status when it materially affects inclusion; an explicit broad scope or accepted unrestricted option satisfies that input. Do not substitute a demonstration mandate or silently unrestricted filters for an unresolved material choice.

## Categories and text

Resolve each needed category on the current run, reusing an identifier already resolved in that run. If no category matches the thesis precisely, use a broader resolved category plus a distinctive text predicate. Resolve the text field and operator before use.

When refining text:

1. Apply all structured mandate filters first.
2. Combine distinctive phrases or related identifiers in one predicate when live-confirmed operator semantics preserve the intended logic. Record whether alternatives are combined with AND or OR; do not fan out across synonyms by default.
3. Follow the workflow's query plan: for a default first-pass landscape, use up to three segment query plans and one highest-noise refinement. Broader user scope and necessary pagination take precedence. Union and deduplicate result sets when multiple plans are needed.
4. Read descriptions before excluding a candidate.
5. Treat semantic relevance as analyst interpretation, not a hard automatic exclusion.

Record the resolved identifiers, filter values, returned total when available, reviewed count, refinements, and exclusions in the query audit. Keep user filters intact when refining; a broader comparison requires explicit authorization or a separately labeled diagnostic that does not replace the requested result.

## Current-state fields

Current status, employee band, and rank movement describe the returned record at query time. Do not describe an undated field as having changed unless a prior snapshot supplied in the task proves the difference.
