# Workflow: Pre-Meeting Company Snapshot

Goal: create a concise, Crunchbase-grounded meeting snapshot with an optional appendix. Do not present it as full commercial, technical, or investment diligence.

## Procedure

1. Resolve the company through `entity-resolution.md` and preserve its organization profile URL. When the user supplies a domain as identity evidence, pass it to `cb_expert_resolve_entity`. Use the structured domain fallback only when the resolver errors or returns no usable match or candidates; never browse the domain unless the user separately asks for external research.
2. Resolve organization card IDs through `cb_reference('entities/organization/cards')` once per session.
3. Call `cb_entity_get` with explicit top-level fields and only the cards needed. Do not request default organization cards. A useful initial selection is:
   - Fields: identifier, short and full description, website, categories, locations, founded date, funding total, employee band, status, IPO status, latest leadership-hire date, and latest layoff date
   - Cards: funding rounds, founders, current employees, similar organizations, leadership events, and layoff events
4. Paginate any selected card when its response indicates more entities and the additional records matter to the snapshot.
5. For one or two decision-relevant founders, resolve person cards and request only current jobs, past jobs, education, and founded organizations.
6. Build competitive context from returned similar organizations and a structured organization search. Evaluate competitors on buyer, product, business model, geography, and stage. Include two to five credible competitors; use fewer when the evidence supports fewer.
7. Batch-search competitor organizations for profile links and relevant positioning fields.
8. Separate retrieved facts from interpretation and questions to test in the meeting.

## Core output

- **Company:** linked canonical name, one-line description, as-of date
- **Why it may fit:** conditional on the supplied mandate
- **Product and buyer:** two or three sentences
- **Financing:** total plus a compact round summary
- **Team signals:** founders, relevant prior roles, current employee band, and dated leadership or layoff events
- **Competitive context:** credible peers and explicit comparison dimensions
- **Principal risks and questions to test:** evidence-linked, not forced objections
- **Suggested meeting focus:** two or three next questions
- **Source notes:** use `—` conventions from `output-contract.md`

## Optional appendix

Add a complete funding table or expanded competitor table only when it improves the user's preparation. Keep the core snapshot near one page.
