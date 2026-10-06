# Private-company research replay corpus

This first collection has **63 cases** across the five skills: 27 development, 28 regression, and 8 held-out cases. Each case has a distinct identifier and a scenario family. Related clarification and accepted-follow-up cases stay in the same split. Held-out scenarios are reserved for final assessment; do not use their results to tune instructions and then continue calling them unseen holdouts. If exposed for debugging, retire or reclassify those cases and create new held-out families.

The holdout is a public, versioned evaluation partition, not a secret benchmark. It shares fictional entities and the provider fixture with other splits. Its separation tests new combinations of behavior within this domain; it does not establish generalization to unseen sectors, accounts, models, or production data. Independent reviewers should add privately authored challenge cases before a broad launch.

## Files

- `suite.json` contains user turns, fixture switches, deterministic checks, and semantic rubrics. The agent receives user turns and common context, never checks or rubrics.
- `base_data.json` contains entirely fictional companies, funding, people, canonical identifiers, profile URLs, list state, and supported metadata. This is runtime evidence, not expected answers.
- `build_corpus.py` rebuilds both files deterministically using only the Python standard library. It does not call any external service.

The frozen as-of date is September 30, 2026. Company names and financial data are fictional. Profile URLs preserve the provider-shaped link format solely for output checks; they are not real company records and must not be browsed.

## Coverage

The corpus covers complete requests and missing inputs, accepted answers in real resumed turns, ambiguous entities and lists, broad versus restricted scope, financial nulls and explicit zeros, exact monetary boundaries, dated events, full pagination and interrupted retrieval, list authorization and persisted state, uncertain and partial writes, hostile text in tool records, and nearby tasks that should not activate these workflows. Five `smoke` cases provide one representative successful path per skill.

Every case has a semantic rubric requiring explicit independent human review. Model judgments may help triage but are not authoritative release approvals. Tool-call presence and state checks establish only specific observable properties; they do not prove a useful or accurate answer. Reviewers must quote evidence for all judgments and check the full user-visible turn sequence, including commentary and intermediate previews when available. Each authorized-write case has its own critical semantic gate for a preview before the first mutation, judged from timeline evidence. A preview that only appears after the write fails even if the final membership is correct. Separate deterministic state checks protect every pre-existing non-target list; append scenarios also verify retention of existing target members.

Negative routing checks apply to skill activation only in the candidate arm. Common task and write-safety expectations apply equally with and without skills. The fixture contains no hidden grading instructions or policy hints; it provides neutral tool semantics and data.

## Provider fidelity and limits

The nine tool input envelopes were inspected from the connected Crunchbase MCP definitions on September 30, 2026. Profile retrieval uses labeled `properties` arrays and relationship `cards` arrays, including per-card pagination. Search validates supported field IDs, operators, value types, enum values, known identifiers, projections, and UUID cursors. List changes persist between resumed turns and attempted calls—including errors—are logged.

This server implements a bounded subset, not the production service. Collection field references expose the fixture's supported contracts. Recursive related-entity subqueries return an explicit `UNSUPPORTED_FIXTURE` response. Only selected cards have populated data; other listed cards are empty. Full entitlement behavior, timing, real identity-ranking accuracy, remote outages, and provider-scale metadata are outside coverage. A model failure caused by unsupported fixture capability should be labeled infrastructure/coverage-limited after reviewing the trace, not silently scored as skill failure or silently discarded.

## Calibration record

During infrastructure pilot calibration on September 30, 2026, a live metadata check confirmed that `person.description` is a supported biography field. The fictional person fixture now includes it. The blanket zero-tool-error gate was also removed prospectively: a validation error followed by a targeted metadata refresh, correction, bounded retry, and supported completion is recoverable behavior, not automatic task failure. Tool errors remain in the complete event ledger and diagnostic report. Explicit call budgets, case-specific failure handling, write safety, and semantic outcome requirements still apply.

Earlier pilot runs keep their original frozen fixture and rubric versions; these changes do not erase or retroactively relabel their errors. Full release assessment must use the revised frozen inputs.

Run the corpus alongside separate live read-only compatibility checks. Saved-list mutation scenarios here never write to an actual Crunchbase account.

The October 5 revision retires seven inspected or repaired holdouts into regression and adds three resolver recovery boundary cases. The remaining public partition is not newly sealed evidence. The September 30 frozen suite and scores remain unchanged in their original run artifacts. Interrupted-search fixtures target successful calls on the relevant collection; partial-write fixtures reject a fixed UUID independently of batching.
