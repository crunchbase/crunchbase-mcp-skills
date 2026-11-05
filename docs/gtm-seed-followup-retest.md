# Named-seed follow-up: targeted contract retest

Run: `evals/artifacts/gtm-seed-followup-repair/run-20261105T223742Z-69549722`.

Reviewed both completed trials of `prospect-missing-seed-supply-seed` (candidate and no-skill baseline, one repetition each), including both turns, source calls/results, captured normalized inputs, final JSON/CSV and final claims. This is machine advice, not human acceptance. No source changes, fixture changes or additional runs were performed by this review.

The repair was prospective and limited to the public case's second-turn request/rubric: retrieve both similarity directions completely, treat ten as a maximum rather than a quota, and obtain approval before adding broader-category matches. No skill changed. This tests behavior under the clarified contract; it does not retroactively change the original export-review item 7 evidence or mark that item accepted/failed.

| Check | Candidate | Baseline |
| --- | --- | --- |
| Initial missing-seed turn | Asks for seed; zero connector calls | Asks for seed; zero connector calls |
| Named seed | Resolver confirms canonical Lumenquill UUID | Resolver confirms same canonical UUID |
| Forward retrieval | source=seed query, 1 returned / 1 reported | source=seed query, 1 returned / 1 reported |
| Reverse retrieval | target=seed query, 0 returned / 0 reported | target=seed query, 0 returned / 0 reported |
| Scope and maximum | Worldwide/all sizes/all stages; returns one, no category fill | Same; returns one, no category fill |
| Exclusion | Seed absent from final output; preserved as exclusion | Same |
| Scoring evidence | Numeric growth 79 + tier p200_positive_low; heat69/delta5; recent Series B; prediction null | Same returned/normalized values |
| Export | Brambleflux UUID, 81/A/rank1; JSON/CSV agree | Same UUID, 81/A/rank1; JSON/CSV agree |
| External mutations | None | None |

Both agents now retrieve forward and reverse searches explicitly rather than relying on one similarity card or replacing the requested relationship with category resemblance. Counts reconcile with returned records; no further pages are indicated. Because this fixture contains only one forward record and zero reverse records, it proves direction coverage but does not stress multiple-page retrieval.

Both source-to-score chains support growth74.5, heat71.5 and funding100, producing rounded81. Null funding prediction remains null. Neither fills the maximum with unrequested broader candidates. Captured final outputs contain the single verified similarity target and match final claims. Missing artifacts on the initial clarification turn are expected; all three requested artifacts are captured on the completed follow-up turn.

A pre-existing interface distinction remains: baseline's normalized/result `url` is the company website, while canonical Crunchbase source URL is retained separately; candidate uses the canonical profile in `url`. This is not a newly repaired property or fabricated identity. It is outside the narrow direction/category-expansion concern. The candidate also retains the source similarity UUID, direction and shared category in its normalized evidence. The source similarity record's display label mentions another company, but its canonical target UUID and separately retrieved organization consistently identify Brambleflux; neither final invents that other company as a result.

Evidence locations: the run's `trials/prospect-missing-seed-supply-seed__candidate__r001/` and corresponding `__baseline__r001/` directories, especially `trial.json` captured artifacts/tool_attempts, `tools.jsonl`, and `turns/2/final.txt`. Original behavior remains preserved in `gtm-export-capture-comparison/run-20261105T204654Z-03324185` and earlier review documents.

No new defect in the specifically clarified direction, coverage, maximum-count or broader-match boundary was established. Human disposition of original item7 remains pending; this one-repetition paired retest is supporting evidence, not a broad release gate or human signoff.

## Explicit user decision

Victor approved all three revised-baseline judgments with “pass next” after the evidence and recommendation. Labels are preserved in `evals/artifacts/gtm-seed-followup-repair-review/human-labels-baseline-approved.json`. This is assistant-assisted, unblinded human approval, not independent calibration. The revised candidate remains pending, and original item7 is not retroactively approved.
