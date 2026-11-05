# Radar and Prioritize diagnostic capture results

Reviewed the completed run `evals/artifacts/gtm-export-capture-comparison/run-20261105T204654Z-03324185`: seven Radar/Prioritize cases, both arms, one repetition, 14 trials and 16 turns. All 50 expected final-delivery artifact files are present, parseable, and match the SHA256 recorded in their trial capture. This closes the missing-byte review gap for this selected slice. It does not establish repeatability, human semantic acceptance, or release readiness.

Reviewer disclosure: this reviewer authored the prospective capture contracts/checks being exercised, but did not author the Radar/Prioritize skill implementation. The review therefore has contract-author overlap; it is machine advisory, not independent human approval. No source changes, reruns, fixture changes, or human labels were made during this review. Newly required outputs are evaluated prospectively; old runs are not retroactively failed for omitting them.

Raw bounded comparison results and artifact hashes are retained in `evals/artifacts/gtm-upgrade-evidence/export-capture-review/radar-priority-audit.json`. Every evidence path below is relative to the run directory. The raw index records source normalization comparisons, independent arithmetic, source-page equality, input preservation, and capture hashes. It is not a judge-label file.

## Outcome matrix

| Case | Retained files, both arms | Substantive result |
| --- | ---: | --- |
| `market-radar-happy` | 10/10 | Both retain the seven-company taxonomy scope and 15 rounds: eight current, seven prior. Four of seven growth tiers are very likely; two of seven founding dates meet youth window. No eligible peer set, no directional label, no focus. |
| `heldout-radar-overlap` | 10/10 | Same seven-company/15-round source population and correct no-direction result. Both explicitly warn against summing overlapping company/round memberships. This inspected historical ID is regression, not fresh holdout evidence. |
| `radar-insufficient-artifact` | 8/8 | Both retain the unchanged supplied input plus result, handoff, and newly captured segment CSV. One company, zero rounds, missing growth/founding evidence: null direction/score/shares, empty focus and handoff. No requery. |
| `prioritize-accounts-followup` | 6/6 | Both wait for the selected book, then deliver three canonical accounts: Lumenquill 88/A, Mossrelay 87/A, Brambleflux 81/A. Shared disclosed policy removes the old baseline undefined-rubric issue. |
| `prioritize-accounts-access-failure` | 4/4 | Both stop after one denied provider operation. Three user-input rows retained as unverified; blank CSV scores/tiers/ranks and null JSON scores/ranks (tier null in candidate, empty string in baseline); `complete:false`, blocked reason and `input_identity_verified:false`. |
| `priority-null-factor` | 6/6 | Both retain three accounts: Mossrelay 87/A/rank 1, Brambleflux 81/A/rank 2, Lumenquill unscored with missing heat and 2/3 factor coverage. CSV and JSON agree. A `list_uuids` ambiguity is noted below. |
| `priority-duplicate-book` | 6/6 | Both deduplicate four supplied rows into exactly three canonical accounts, preserving the same 88/87/81 order and A tiers; no distinct account lost. |

All completed outputs in this slice agree with their final summaries on the reviewed rows, counts, scores, unknowns, scope and exclusions. Provider-call sequences contain no external writes. The overall diagnostic run remains `needs_review` and `release_gate:not_ready`; this report does not override that status.

## Source and arithmetic review

For all four natural-Radar trials, `turns/1/artifacts/source-records.json` exactly equals the successful search pages returned in `tools.jsonl`, grouped by collection. The normalized organization identifiers, growth/funding values and founding dates, and normalized round identifiers, company joins, dates and USD amounts match those pages. Both arms preserve the taxonomy population, including the description-misaligned company, rather than dropping it from the primary denominator.

Independent counting uses current dates `(2025-11-05,2026-11-05]` and prior dates `(2024-11-05,2025-11-05]`: eight versus seven rounds. Known current amounts total $28M across seven disclosed amounts plus one unknown; prior amounts total $26M across six disclosed amounts plus one unknown. Unknown amounts remain null rather than zero. Growth share is 4/7; youth share is 2/7. Seven companies fall below the disclosed minimum 15, and zero eligible segments fall below the required three peers. Direction/score/focus are therefore withheld correctly. Candidate overlap's final $28M/$26M figures match both source pages and result JSON. No unsupported median is asserted in this run.

For all six scored Priority trials, normalized growth score/tier, heat score/delta, completed-funding date/type match retrieved evidence; final CSV/JSON scores match independently recomputed results. Lumenquill: growth (80+100)/2=90, heat 70+5/2=72.5, recent financing 100, weighted 87.75→88. Mossrelay: 89,70.5,100→86.75→87. Brambleflux: 74.5,71.5,100→81.25→81. Missing heat leaves Lumenquill's score/tier/rank null without reweighting in the null-factor case. Missing funding amount does not erase the known qualifying recent financing date.

The followup baseline retrieves prediction cards in addition to organization fields. Its non-null funding tier is supported by the returned card; the candidate leaves the profile-level absent funding tier null. Both scores legitimately use the maximum recent-financing component. This difference is not fabricated evidence or an arithmetic mismatch. The baseline preserves its explicit normalization preference and raw card evidence, including the conflict between Brambleflux's profile growth tier and its card; it uses the non-null profile tier. A reviewer should preserve this provenance distinction rather than compare normalized nulls mechanically across arms.

For insufficient Radar, the captured input bytes equal the inline attachment bytes in both arms. Its complete retrieval coverage does not turn absent growth/founding evidence into observations. Both outputs preserve that distinction and empty downstream selections. In the access-failure Priority pair, both CSV and JSON preserve the supplied identities as input provenance and never call them verified records.

## Handoff and interface questions for the next reviewer

1. **Unscored UUID in baseline selection field.** `priority-null-factor__baseline__r001/turns/1/artifacts/priorities.json` includes unscored Lumenquill in `list_uuids`; candidate excludes it. Both still display it correctly as insufficient evidence, with no rank. The shared attachment requires `list_uuids` but does not explicitly state that it must contain only scored/actionable rows. Consequently this is a downstream-consumption risk and shared-contract ambiguity, not a fair hidden-rule baseline failure. Do not automatically execute either handoff. A future contract revision should explicitly define selection eligibility before adding an exact membership oracle.

2. **Normalized URL/count interoperability.** Baseline followup and duplicate-book `candidates.json` use the company website in `url`, preserve the Crunchbase profile separately in `source_url`, and set `run.count:null` for the complete book. The user-facing CSV profile column is correct and all rows remain present. Candidate uses a profile URL and numeric count. This is not lost source identity, but a consumer expecting the candidate helper's narrower input shape cannot assume direct interchangeability. The shared contract should explicitly define URL semantics and whether an unlimited count may be null before treating these differences as acceptance failures.

3. **Coverage booleans have different scopes.** Natural-Radar candidate happy marks returned pagination complete and separately marks full-market coverage false; baseline marks coverage false while recording exhausted query pages. Both preserve the bounded-sample qualification. Do not interpret the booleans as opposite claims about real-world market exhaustiveness. Future consumers need an explicit distinction between retrieved-page completeness and market coverage.

4. **Optional statuses differ without changing the decision.** Radar uses candidate `too_small`/`insufficient_evidence` and baseline `ineligible` while both leave direction/score null and top-level status insufficient. Shared policy does not enumerate segment-level status strings. Compare the supported decision and evidence, not implementation-specific status labels.

These observations are raw next-review advice, not requests to change this frozen run. The exact captured bytes now permit a human to adjudicate them. No material candidate scoring, source-normalization, scope-preservation, or missing-output defect was established in this seven-case slice; broader claims remain unsupported by this one-repeat diagnostic.
