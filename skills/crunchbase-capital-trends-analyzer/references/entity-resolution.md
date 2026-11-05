# Entity Resolution

Resolve every company to a canonical organization before profile analysis, saved-list work, or monitoring.

## Resolution order

1. **Expert resolver.** Call `cb_expert_resolve_entity` first for every named company, investor, person, or other canonical entity. Supply the narrowest collection, such as `organizations`, and concise industry, geography, workflow, or neighboring-entity context. Pass `domains` only when the user supplied the domain or it came from a previously resolved record; never invent or infer a domain from model memory. For identity-only work, pass `cb_entity_get: null` so profile retrieval remains separately scoped and auditable.
2. **Resolver result.** When the result is one confident match, preserve its identifier and profile URL, but first reconcile all supplied identity anchors under the conflict rule below; resolver confidence does not override a contradictory supplied name or domain. When it returns ranked candidates, evaluate those candidates directly; do not call autocomplete merely to obtain a second ranking. Ask the user to choose when multiple candidates remain credible.
3. **Structured domain fallback.** Only when the resolver has a recoverable outage or returns no usable match or candidates and the user supplied a domain, resolve `website_url` through `cb_reference` and use `cb_search_query` with the live-supported domain operator. For several supplied domains, use the live-supported batch operator and reconcile every input. Treat the domain as an identifier, not as permission to browse the site or invoke another app.
4. **Autocomplete fallback.** If the resolver had a recoverable outage or produced no usable match or candidates and a structured domain lookup did not resolve the entity, query the distinctive name with `cb_entity_autocomplete(collection_ids="organizations")`. Remove generic legal or marketing suffixes only when doing so preserves the distinctive identity.
5. **Name-only fallback.** If autocomplete results are dominated by description matches, resolve `identifier` and `rank_org` through `cb_reference`, search the bare name with the supported name operator, and sort by organization rank as a tiebreaker.
6. **Parent or legal name.** If a product is filed under another organization name, try the parent or legal name supplied by the user or visible in returned candidates.

## Error boundaries

Authentication, permission, and metering errors are terminal: report them and stop. A resolver-only unavailable/timeout response permits the fallback sequence above within Crunchbase. Attempt each applicable fallback once per unresolved input; stop if a fallback itself has a service or access failure. Do not restart the resolver or cycle through spellings. A successful fallback still requires identity confirmation; credible alternatives require a user choice. For other service failures, disclose the incomplete work.

## Conflicting supplied identity anchors

A supplied company name and domain are joint constraints, not competing hints with an automatic domain winner. If returned evidence associates them with genuinely different organizations, pause work that depends on that entity’s identity, including profile analysis, screening, scoring and saved-list changes. Ask one concise question naming the conflicting inputs and any returned linked candidates so the user can select the intended account. Do not choose the domain match, silently replace the name, or treat either candidate as confirmed while awaiting the answer.

A verified alias, rebrand, legal name, or equivalent identity relationship may reconcile different wording: proceed when returned evidence establishes that both supplied anchors refer to the same canonical organization, and state the relevant relationship briefly. Mere similarity, resolver confidence/rank, an assumed acquisition, or a domain redirect not established by returned evidence is insufficient. If resolving the discrepancy needs more data, retrieve only the minimum identity evidence; do not expand into downstream research. Reuse an explicit user correction or previously established identity decision. Independent confirmed entities in a multi-entity request may proceed, with the conflicting entity clearly pending; pause aggregate results when that unresolved identity could change their membership or denominator.

## Confirmation rules

- Never accept the first resolver or autocomplete candidate solely because it ranks first.
- Confirm identity using the website, short description, canonical name, and organization prominence together.
- Use rank only to order or break ties; do not display it as a quality score.
- When one match is clear and supplied identity anchors are reconciled, proceed and show the canonical linked name.
- When multiple candidates remain credible, ask the user to choose among the linked candidates.
- When no canonical match is confirmed, identify the unresolved input and continue with the confirmed set unless that entity is essential to the task.

For a batch, report requested, confirmed, ambiguous, and unresolved counts before any saved-list write.
