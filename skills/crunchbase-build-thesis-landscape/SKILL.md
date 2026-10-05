---
name: crunchbase-build-thesis-landscape
description: Discover, segment, screen, and optionally save a Crunchbase company landscape against an investment thesis, including asking for a thesis anchor when an explicit Crunchbase landscape request omits one. Use only when the user explicitly asks to use Crunchbase, selects Crunchbase as the data source, or follows up on an active Crunchbase landscape. This skill owns compound “build and save” requests. Do not use for a single-company brief, analysis of a user-confirmed company universe, operations on an existing saved list, recent-round-only reviews, public-equity research, Crunchbase pricing or account support, or generic landscapes when Crunchbase was not requested.
license: MIT
---

# Crunchbase Thesis Landscape

Build a reviewed company universe against an explicit thesis. Segment by buyer, product, use case, or business model; do not treat keyword matches as final relevance decisions.

## Clarification contract

1. Reuse the user's mandate and accepted scope from the conversation. Require a usable thesis anchor such as a market, buyer, product, use case, business model, or category, or an explicit request for a broad private-company landscape.
2. Ask about unresolved geography, stage, funding cap, or operating status when the choice would materially change which companies qualify. Bundle the blocking choices into one concise question; offer a concrete proposed scope, including unrestricted options, for the user to accept. Do not silently treat an omitted material filter as unrestricted or apply a demonstration mandate.
3. Do not ask for preferences that cannot affect the requested result. An explicit broad scope or acceptance of a proposed scope is sufficient. “Use the defaults” accepts only defaults already disclosed in the conversation; otherwise propose them and wait. Do not re-ask answered questions or seek authorization already given.
4. Before resolving missing material scope, make no Crunchbase search. A broad but usable thesis such as “healthcare AI” supplies the thesis anchor, but does not answer other material mandate questions. Ask again only if the answer introduces a new blocking ambiguity.

## Operating contract

1. Before a structured search, resolve the required predicate and order contracts through `cb_reference` unless a successful resolution is already available in the current session. Reuse valid contracts and refresh only the affected metadata once after a validation error, as specified in `references/query-core.md`. Do not resolve projection-only fields. Prefer one collection-level catalog, then request only details it does not expose.
2. Resolve categories and locations with `cb_entity_autocomplete`. For named companies, investors, or people, use `cb_expert_resolve_entity` first. It is the only allowed expert tool; never call another tool whose basename contains `expert`. Use autocomplete for a named entity only after the resolver has a recoverable outage or returns no usable match or candidates.
3. Never invent or infer a domain from model memory. Use only domains supplied by the user or returned by a resolved record.
4. Search and analysis are read-only. Call `cb_list_create` or `cb_list_add_entities` only when the user explicitly asks to save or create the discovered landscape. Preview the collision-free list name and linked canonical companies before the first write.
5. For a first pass, aim to issue the first `cb_search_query` within 12 Crunchbase calls and finish within 16 calls for read-only work or 20 for build-and-save. These are efficiency targets: required contracts, the requested scope, necessary pagination, and write reconciliation take precedence. Never weaken user filters to meet a target. Reuse search projections; do not call `cb_entity_get` for fields already returned by the search.
6. After an authorized write, call `cb_list_get` to reconcile persisted membership. Once reconciliation succeeds, make no further tool calls and render the final result immediately.
7. Use neutral record language. Show `—` for a null; the legend is “— indicates no value was returned for that field.” For an empty search, say “No records matched the stated filters.” Disclose observed, decision-relevant limitations as specified in `references/output-contract.md`; never infer that an event did not occur from an absent record.
8. Link company names to organization profile URLs. Include as-of date, segments, filters, denominator, refinements, and concise exclusions. Resolve every bundled `references/...` or `scripts/...` path relative to the directory containing this `SKILL.md`. Never mention skill folders, skill or reference files, instruction loading, plugin or package paths, caches, or attempts to locate bundled resources in any user-visible message.
9. Stop on authentication, permission, or metering errors. A resolver-only outage permits the bounded same-provider fallback; other service failures require an accurate limitation. For an uncertain authorized write, reconcile persisted membership before considering a retry, as specified in the saved-list reference. Do not substitute another data source unless the user requested external research.

## Procedure

1. Read `references/landscape-build.md`, `references/query-core.md`, `references/organization-search.md`, and `references/output-contract.md`.
2. Read `references/entity-resolution.md` when the request names a company, investor, person, parent, or domain.
3. Read `references/calculation-spec.md` when deriving recency or other metrics; use `scripts/derive_metrics.py` when applicable.
4. Read `references/saved-lists.md` only when the same request explicitly asks to save the new landscape.
5. Apply the confirmed mandate and retain private-company scope. Use unrestricted geography, stage, funding cap, or operating status only when the request or accepted proposal establishes that scope; state the applied scope and as-of date.
6. For a default first pass, use up to three segment query plans and one audited refinement plan. Follow a broader user-requested scope; necessary pagination is not another refinement. Deduplicate by organization UUID, review descriptions, and present the candidate universe before any authorized save. Label a bounded result as a first pass, and retrieve all pages when the user requests a complete landscape.
