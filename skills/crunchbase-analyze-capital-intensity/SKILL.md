---
name: crunchbase-analyze-capital-intensity
description: Analyze funding concentration, capital intensity, formation, or market timing across a user-confirmed private-company universe using Crunchbase, or ask the user to confirm a universe when an explicit Crunchbase capital or overfunding question omits one. Use only when the user explicitly asks for Crunchbase, selects Crunchbase as the data source, or follows up on an active Crunchbase capital analysis. Do not use for open-ended company discovery, recent-round sourcing, a single-company brief, saved-list membership changes, public-equity research, Crunchbase pricing or account support, or generic market analysis without Crunchbase.
license: MIT
---

# Crunchbase Capital Intensity

Analyze capital deployment only within a confirmed company universe. Never generalize a confirmed-list result to the whole market.

## Clarification contract

1. Reuse the confirmed universe and analytical scope from the conversation. Company names, one selected saved list, or an explicitly confirmed candidate set define the universe; a sector label or thesis alone does not.
2. Ask for any unresolved period, comparison window, or capital definition that materially changes the calculation. Offer concrete choices, such as a trailing 24-month funding period and 12-month comparison, as proposals requiring acceptance rather than automatic defaults. Do not ask when the requested metric or prior context already determines them.
3. If the universe or material analytical scope is absent, make no data-retrieval call. Bundle blocking inputs into one concise question. “Just run it” or “use the defaults” accepts only a previously disclosed proposal and cannot supply an undefined universe. Do not re-ask answered questions or seek authorization already given.
4. When supplied names or a selected list are ambiguous, make only the minimum resolver or list-identification call needed to expose credible choices, then ask once. Ask again only if the answer introduces a new blocking ambiguity.

## Universe gate

Require company names, one selected Crunchbase saved list, or an explicitly confirmed candidate set before retrieval. If no universe is confirmed, propose concise universe options and ask the user to choose without calling Crunchbase tools.

## Operating contract

Tool names below are Crunchbase basenames. Resolve them to the actual fully qualified names exposed by the connected Crunchbase server before calling them; do not guess a host prefix. If a required capability is unavailable, report the missing connection or tool and stop the dependent work.

1. For named companies, investors, or people, use `cb_expert_resolve_entity` first. It is the only allowed expert tool; never call another tool whose basename contains `expert`. Use returned candidates directly and ask when several remain credible. Use `cb_entity_autocomplete` for a named entity only after the resolver has a recoverable outage or returns no usable match or candidates.
2. Use only user-supplied or previously resolved domains. Never invent or infer a domain from model memory.
3. Before a structured search, resolve the required predicate and order contracts through `cb_reference` unless a successful resolution is already available in the current session. Reuse valid contracts and refresh only the affected metadata once after a validation error, as specified in `references/query-core.md`. Do not resolve projection-only fields.
4. Deduplicate the confirmed universe by organization UUID. Report requested, confirmed, ambiguous, unresolved, and analyzed counts.
5. Keep this analysis read-only, including when the universe comes from a saved list. Never create, append, replace, or otherwise modify list membership within the analysis. Handle an explicit list-change request as a separate saved-list workflow; analysis alone does not authorize it.
6. Calculate full months, trailing periods, medians, formation, and concentration exactly as specified. Exclude `—` amounts from money calculations while reporting their count.
7. Use neutral record language. Show `—` for a null; the legend is “— indicates no value was returned for that field.” For an empty search, say “No records matched the stated filters.” Disclose observed, decision-relevant limitations as specified in `references/output-contract.md`; never infer that an event did not occur from an absent record.
8. Include the as-of date, confirmed universe definition, denominator, time windows, and formulas. Separate retrieved facts, derived metrics, interpretation, and suggested actions. Resolve every bundled `references/...` or `scripts/...` path relative to the directory containing this `SKILL.md`. Never mention skill folders, skill or reference files, instruction loading, plugin or package paths, caches, or attempts to locate bundled resources in any user-visible message.
9. Stop on authentication, permission, or metering errors. A resolver-only outage permits the bounded same-provider fallback; other service failures require an accurate limitation. Do not retry a failed fallback or invent identifiers. Do not substitute another data source unless requested.

## Procedure

1. Read `references/market-analysis.md`, `references/calculation-spec.md`, and `references/output-contract.md`.
2. Read `references/entity-resolution.md`, `references/query-core.md`, `references/organization-search.md`, and `references/funding-round-search.md` for a named universe.
3. Read `references/saved-lists.md` only when a selected saved list supplies the universe; use its read operations only.
4. Use `scripts/derive_metrics.py` for supported deterministic calculations.
5. Present metrics within the confirmed universe, alternative explanations, and questions that would change the interpretation.
