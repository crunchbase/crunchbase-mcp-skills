---
name: crunchbase-prepare-company-brief
description: Resolve a private-market entity and prepare a concise Crunchbase-grounded pre-meeting company brief or snapshot, including asking for the company when an explicit Crunchbase brief request omits its identity. Use only when the user explicitly asks for Crunchbase, selects Crunchbase as the data source, or follows up on an active Crunchbase company brief. Do not use for broad landscapes, recent-round screens, market-wide capital analysis, saved-list operations, public-equity research, Crunchbase pricing or account support, or generic company research when Crunchbase was not requested.
license: MIT
---

# Crunchbase Company Brief

Prepare a focused company snapshot for meeting preparation. Do not present it as full commercial, technical, or investment diligence.

## Clarification contract

1. Reuse a company name, user-supplied domain, or previously resolved company identity from the conversation. If none is present, make no Crunchbase call and ask for the company.
2. Ask for meeting purpose, audience, or mandate only when the requested tailoring depends on an unresolved choice. Bundle blocking inputs into one concise question; offer alternatives as proposals rather than selecting them for the user.
3. A request for an untailored company brief is enough to prepare a general brief. Do not ask about irrelevant preferences, re-ask answered questions, or seek authorization already given. “Use the defaults” accepts only previously disclosed defaults; propose any material default that has not been disclosed and wait for acceptance.
4. When identity evidence is supplied, make the minimum resolution call. Ask the user to choose only if several credible candidates remain. Ask again only if the answer introduces a new blocking ambiguity.

## Operating contract

Tool names below are Crunchbase basenames. Resolve them to the actual fully qualified names exposed by the connected Crunchbase server before calling them; do not guess a host prefix. If a required capability is unavailable, report the missing connection or tool and stop the dependent work.

1. Resolve the named company first with `cb_expert_resolve_entity`, using the narrowest collection, concise situational context, and `cb_entity_get: null` for identity-only resolution. It is the only allowed expert tool; never call another tool whose basename contains `expert`.
2. Use a confident resolver match directly. When the resolver returns several credible candidates, show linked choices and ask the user to select. Use `cb_entity_autocomplete` only when the resolver has a recoverable outage or returns no usable match or candidates.
3. Pass a domain only when the user supplied it or it came from a previously resolved record. Never invent or infer a domain from model memory. A supplied domain is identity evidence, not permission to browse it.
4. Retrieve the profile separately with `cb_entity_get`, explicit top-level fields, and only decision-relevant cards. Never request default cards.
5. Before a structured search, resolve the required predicate and order contracts through `cb_reference` unless a successful resolution is already available in the current session. Reuse valid contracts and refresh only the affected metadata once after a validation error, as specified in `references/query-core.md`. Do not resolve projection-only fields. Reuse returned similar organizations and search projections; keep the competitor query set bounded to the requested scope.
6. Keep this skill read-only. Never call a `cb_list_*` write tool.
7. Use neutral record language. Show `—` for a null; the legend is “— indicates no value was returned for that field.” For an empty search, say “No records matched the stated filters.” Disclose observed, decision-relevant limitations as specified in `references/output-contract.md`; never infer that an event did not occur from an absent record.
8. Link the canonical company and competitors to organization profile URLs. Include the as-of date and state that the brief is Crunchbase-grounded. Separate facts, interpretation, risks, and questions to test. Resolve every bundled `references/...` path relative to the directory containing this `SKILL.md`. Never mention skill folders, skill or reference files, instruction loading, plugin or package paths, caches, or attempts to locate bundled resources in any user-visible message.
9. Stop on authentication, permission, or metering errors. A resolver-only outage permits one same-provider fallback sequence; other service failures require an accurate limitation. Do not retry a failed fallback or invent identifiers. Do not substitute external research unless the user requested it.

## Procedure

1. Read `references/entity-resolution.md` before resolving identity.
2. Read `references/company-snapshot.md`, `references/query-core.md`, and `references/output-contract.md` before profile retrieval and composition.
3. Retrieve only the company, financing, team, event, and peer fields needed for the requested meeting context.
4. End with the strongest counterinterpretation or question that could materially change the assessment.
