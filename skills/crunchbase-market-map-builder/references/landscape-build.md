# Workflow: Thesis Landscape

Goal: build a reviewed, segmented company landscape against an explicit thesis and screening mandate.

## Procedure

1. For an agreed exploratory first pass, translate the thesis into up to three proposed sub-verticals based on buyer, product, use case, and business model. Expand when the requested scope requires it. Show segment definitions in the deliverable so the user can correct them.
2. Resolve each unique category and location once. Resolve all predicate and order fields on the current session, preferably with one collection-level fields reference. Use a targeted field reference only when the collection response does not expose a needed operator, enum, or value shape. Projection-only output fields do not need reference calls.
3. Apply the user's confirmed mandate before text refinement. Preserve private-company scope using the live-confirmed company facet and private IPO status. Reuse geography, funding boundary, target stages, and operating status already supplied or agreed. Ask about omitted dimensions when they materially affect the result; an unrestricted dimension is an option the user can accept, not an assumption inferred from omission.
4. Start with one query plan per sub-vertical. Request canonical identifier, description, categories, location, funding total, latest funding date/type/amount, employee band, founding date, investors, and website.
   - Aim for a valid first search within 12 Crunchbase calls and roughly 16 calls for a read-only first pass or 20 for build-and-save. These are efficiency targets, not completion limits. Requested scope, necessary pagination, contract-error recovery, and authorized write reconciliation take priority; reduce optional enrichment first.
5. For the agreed first pass, allow one refinement plan for the highest-noise segment when a broad text match produces more than 50 results or more than three times a supplied segment target. Use distinctive phrases with live-confirmed operator semantics; avoid separate queries for every keyword or synonym. The default target is four distinct query plans, excluding pagination and validation-error retries. Expand when the user requests deeper or exhaustive discovery.
6. If short-description text does not represent the intended segment, use the full description field in that refinement. Do not loosen user-specified mandate constraints without approval. For exhaustive requests or complete-universe metrics, paginate each final query as required by `query-core.md`; for an exploratory sample, state reported matches and reviewed rows and limit claims to the reviewed denominator.
7. Review descriptions before excluding candidates. Place a company in its best-fit segment once and retain a concise exclusion log.
8. Compute full months since the latest funding date using `calculation-spec.md`. Apply timing labels only; do not infer fundraising intent or company health.
9. Obtain and preserve each organization profile URL.
   - Reuse the search projections. Do not call `cb_entity_get` for a candidate when the search already returned the fields needed for the landscape row.
10. Present the reviewed universe before any saved-list write. Follow `saved-lists.md` only if the user explicitly asks to save it.
    - Once `cb_list_get` reconciles an authorized write, stop calling tools and render the final result immediately. Do not reopen discovery or enrichment after the write.

## Output

One table per segment:

| Company | What it does | Total raised | Latest round (type, amount, date) | Full months since | Timing signal | Investors | Relevance confidence |
|---|---|---:|---|---:|---|---|---|

Then include:

- **Review priorities:** candidates ranked against the supplied mandate, with conditional reasons
- **Segment observations:** density and differentiation within the returned, reviewed universe
- **Exclusions and uncertainty:** concise reasons
- **Query audit:** segment definitions, resolved identifiers, structured filters, counts, refinements, and denominator
- **Source notes:** use `—` conventions from `output-contract.md`

The target count is a quality guide, not a quota. Do not pad a segment with weak matches.
