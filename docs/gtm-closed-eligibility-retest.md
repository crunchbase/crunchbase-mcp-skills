# Closed-account eligibility: targeted retest advice

Run: `evals/artifacts/gtm-closed-eligibility-repair/run-20261105T225425Z-bef0302b`.

Reviewed both completed `prospect-missing-seed-accept-icp` trials, candidate and baseline, one repetition each. Evidence includes both-turn prompts/finals, source tools, and all six captured files (`candidates.json`, `prospects.json`, `prospects.csv` for each arm). This is machine advice: no human labels, source edits, fixture edits or additional runs were made by the reviewer.

**Recommendation: pass the revised baseline and candidate for this narrow closed-eligibility concern. No issue requiring a stop was found in the audited criteria.** This recommendation does not retroactively approve the original item 13 or relabel its evidence. The prospective task/rubric clarification—not a skill change—now explicitly requires closed status, null tier/rank and exclusion from actionable list UUIDs; a retained numerical score is allowed only as historical/non-actionable.

| Criterion | Baseline evidence | Candidate evidence | Advice |
| --- | --- | --- | --- |
| Requested scope and account retention | No first-turn retrieval. Explicit second-turn ICP switch; worldwide, all sizes/stages, no exclusions. Nine private source records reviewed for dental fit; all eight dental vendors retained. | No first-turn retrieval. Same accepted scope; exact dental/private query returns eight, all eight retained. | Pass for revised trial. |
| Closed-account eligibility | Gossamervault source is closed; result status closed, score/tier/rank null; CSV score/tier/rank blank; UUID absent from list_uuids. Final states this accurately. | Status closed, tier/rank null, UUID absent from list_uuids. Numerical86 retained consistently in JSON/CSV; final explicitly says historical only. | Pass under clarified permitted alternatives. |
| Evidence and export consistency | Eight normalized inputs, eight JSON rows, eight CSV rows; UUID/score/tier/rank/status match row-for-row. Unknown funding predictions and Mossrelay amount remain null. | Same parity and unknown preservation; seven operating accounts scored 88/87/86/81/80/80/80 with corresponding ranks. | Pass for revised trial. |

Both final files retain the closed company visibly rather than silently removing it or routing it as Tier A. Both actionable UUID lists contain only the seven operating companies. Neither tool sequence makes an external list/CRM/schedule mutation. The baseline repeats its identical source query; this is redundant but does not change the retained population or evidence. Both describe completeness as within returned/synthetic source scope rather than a global market census.

The numeric86 retained by candidate is expressly allowed by the revised requirement and labeled historical in the final answer. It should not be reclassified as a defect by importing a stricter null-score requirement from another case. Conversely, the original baseline's 86/A/rank4 output remains separate evidence of the earlier actionability concern.

Evidence references: run `trials/prospect-missing-seed-accept-icp__baseline__r001/trial.json` and candidate counterpart hold captured files and source calls; `turns/1/final.txt` shows clarification, `turns/2/final.txt` shows scope/closed-account claims, and `tools.jsonl` provides returned organization status and fields. Original evidence is preserved in `gtm-export-capture-comparison/run-20261105T204654Z-03324185` and `docs/gtm-prospect-capture-results.md`.

One repetition per arm is bounded evidence for this clarification, not broad workflow validation or production approval. Human/delegated disposition remains the coordinator's responsibility; this document records only the evidence-bound pass recommendation.

## Oracle correction and delegated disposition

Both model outputs satisfy the clarified rule. The initially added CSV oracle mistakenly supplied only one expected row to an exact-row-count matcher, so the frozen initial report records two deterministic failures. The check now expects all eight UUIDs and constrains the closed row’s status/tier/rank. The retained outputs pass that corrected check; negative checks reject an actionable closed row and any omitted account. No model rerun, task instruction change, trace rewrite, or historical regrade was performed. Evidence is in the run’s `corrected-oracle-assessment.json`; original report remains intact. Six targeted coverage tests and suite validation pass. Both revised cases receive delegated pass recommendations, stored separately from human labels.
