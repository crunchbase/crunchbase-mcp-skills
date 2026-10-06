# Workflow: Recent Funding Review

Goal: identify recently announced rounds in the user's thesis areas, screen them against the stated mandate, and produce a review queue without turning screening signals into investment decisions.

## Procedure

1. Fix the as-of date and confirmed review window. When the window is absent, propose the trailing 30 days and wait for acceptance as specified in `SKILL.md`.
2. Record the confirmed screening mandate and private-company scope. Resolve any material choice about geography, stage, funding cap, or operating status before searching; unrestricted values require support from the request or an accepted proposal.
3. Resolve only the predicate and ordering contracts needed for this screen through `cb_reference`, reusing valid session resolutions. Confirm company/private-company scope through supported search fields or a subsequent organization screen; do not infer private status from a funding round alone.
4. Resolve a location only when requested. For a first pass, use up to three representative category identifiers per thesis area, expanding when required by the user’s scope. Combine related identifiers or text terms in one live-supported predicate with recorded AND/OR semantics; do not fan out across category synonyms.
5. Use one `funding_rounds` query plan per thesis area as the first-pass default so counts and refinements remain attributable. If it returns no records, allow one audited refinement of the category or text mapping while preserving the user’s mandate. Broader explicit scope can require more plans; never relax user filters just to produce matches.
6. Request round identifier, date, type, amount, funded organization identifier, organization description, organization total funding, and lead investors. Paginate when the user requests a complete review.
7. Screen rows against the mandate and record the reason for every exclusion.
8. Batch-search surviving organizations to obtain organization profile URLs and any additional screen fields.
9. Enrich only high-priority review candidates. Retrieve the organization with explicit fields and the `founders_lookup` card, then retrieve one or two relevant people with explicit job and education cards. One company call alone does not establish founder background.
10. Classify each survivor as `review now`, `watch`, or `outside stated screen`, using only the supplied mandate. If check size, ownership, or another decisive criterion is absent, state that the classification is a screening priority rather than an investment recommendation.

## Output

Group by thesis area:

| Company | Round (type, date) | Amount | Lead | What it does | Total raised | Review priority | Rationale |
|---|---|---:|---|---|---:|---|---|

Then include:

- **Review-now queue:** concise next steps tied to the mandate
- **Exclusions:** company and explicit screen criterion
- **Query audit:** as-of date, window, resolved identifiers, filters, returned total when available, reviewed count, and whether retrieval was complete
- **Source notes:** use `—` conventions from `output-contract.md`

Repeated lead investors are an observation to investigate, not proof of thesis momentum.
