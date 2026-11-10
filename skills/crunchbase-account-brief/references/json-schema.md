# Account Brief JSON — account-brief/v2

Return one object and no surrounding commentary when JSON is requested. Save it when an artifact is requested and run `python scripts/validate_brief.py <brief.json>`. The validator checks structure, dates, canonical identity and source presence; it cannot establish the truth or usefulness of prose. Verify those against actual retrieved evidence.

Required shape (the names below are synthetic examples, not defaults):

```json
{
  "schema_version": "account-brief/v2",
  "as_of": "2026-11-05",
  "company": {"uuid": "returned-canonical-id", "permalink": "example-company", "name": "Example Company", "url": "https://www.crunchbase.com/organization/example-company"},
  "scope": {"purpose": "sales first meeting", "event_start": "2026-05-05", "event_end": "2026-11-05", "seller_mode": "product-neutral"},
  "coverage": {"complete": true, "limitations": [], "sources": ["Crunchbase"]},
  "meeting_type": "first",
  "summary": "Evidence-grounded account summary.",
  "talking_points": [],
  "recent_events": [],
  "people": [],
  "competitors": [],
  "crm": null,
  "notes": []
}
```

`scope.seller_mode` is `tailored` or `product-neutral`. Event start/end are both null for a profile-only task; otherwise ISO dates in order, no later than as_of. Scope records accepted filters/window and request purpose. `coverage.complete` describes this agreed retrieval, not complete real-world source coverage. limitations names material unavailable dependencies, unresolved identities, partial pages/cards, and restricted calculations. Never assert complete when limitations establish incomplete retrieval.

`company` may add website, description, hq, employees, status and ipo_status; unknown values are null. All nested company objects retain returned canonical UUID/permalink/URL. `meeting_type` is first or follow_up, based on user or corroborated CRM evidence; `meeting_goal` may be null.

Talking point: `{headline, fact: [{date, fact, source_url, about}], implication, seller_offering, proof, say}`. Facts have a valid occurred-event date and source; about identifies the account or competitor canonical permalink. implication is a hypothesis, seller_offering is null in product-neutral mode, and proof is null unless supported by seller context. Optional `picks_up` links a follow-up to a sourced CRM open item. `opener` and `opener_basis` use the same evidence separation; a generic opener has a null basis rather than a fabricated event.

Events use `{date, type, description, source_url}`. Dates describe actual occurrence/announcement, not ingestion. Future plans belong in a separately labeled `planned_events` section with planned_date, never recent_events. `since_last_meeting` is an event subset strictly after the known last meeting. A missing meeting date cannot establish that subset.

Optional sections preserve the detailed brief capabilities: `funding` (dated/type-labeled rounds, USD amounts or null); `funding_prediction` (provider tier, generated_on, actual returned horizons/probabilities, null when unavailable); `momentum`; `products`; `why_they_might_buy` (offering, buyer, evidence, products_used, confirm_question); `competitor_patterns` with each named member and dated sources; `seller` with confirmed offerings/provenance; `warm_open`; `ipo_prediction`; `growth_insight` with underlying article/date; `segment_calls`; `customer_competitors`; and `investor` with distinct funds and investment activity. Do not manufacture optional values just to fill a shape. Do not equate predicted financing with available budget.

`people` contains supplied attendees with match status, or explicitly unconfirmed key people; retain profession-only source evidence and no email/phone fields. `crm` is null or a labeled source/account-ID object, with actual dated activities, open items, next steps, deals and contacts. Exports without activity text cannot populate meeting summaries. Missing/unknown amounts remain null, currencies remain explicit; do not normalize unknown currency to USD. `notes` carries limitations and any factual uncertainty that prose would otherwise mention.

This schema intentionally replaces pilot version 1.6 with a namespaced version, canonical UUID, scope and coverage. Do not label a v2 artifact as the legacy schema. Consumers must select by schema_version.
