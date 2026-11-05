# Targeted GTM export-capture review

This prospective revision closes eleven existing export-evidence gaps identified by the R3 advisory reports. It does not alter historical run files, skill code, replay fixtures, harness code, source values, answer keys for business outcomes, or human labels. No model trials were launched by this author. Changes are confined to the public GTM suite/README, the new capture-coverage test file, and this document.

## Rationale and scope

R3's natural Prospect and Prioritize cases linked exports that were not allowlisted for capture. Their CSV/JSON content could therefore not be adjudicated from retained bytes. Natural Radar happy/overlap likewise linked helper results/handoffs without retained content. Those two Radar prompts now explicitly request those previously claimed deliverables. The normalized insufficient Radar policy already required a segment CSV, but the allowlist omitted it.

Original task requests and agent claims are different evidence categories. Prospect hostile/access and Priority followup/access/null-factor/duplicate-book already explicitly requested a CSV; their new normalized/result JSON requirements are prospective additions. The two Prospect seed continuations did not explicitly request file exports in their original second turns, but R3 agents claimed CSV/JSON deliverables, so naming and requiring those files now is a prospective task change. Natural Radar happy/overlap likewise did not originally request exact files; their new explicit source/input/result/CSV/handoff chain is prospective. Insufficient Radar already requested exports through its shared policy; only its missing CSV retention/check was incomplete. In particular, access-failure JSON, exact blocked schema, header-only Prospect semantics and unverified Priority-row export are newly disclosed requirements. Historical trials are not failed retroactively for omitting any newly required file or field. Old missing capture means unreviewable retained evidence, not proof of failure to deliver.

The revised shared attachments describe file schemas equally to candidate and baseline; scoring cases use the existing accepted policy and artifact contract, not a hidden helper-only interface. This also corrects the natural Prioritize followup's underspecified numeric policy: baseline now receives the exact fixed rubric before completing the selected book. Artifact checks are arm-neutral. The cases retain their prior semantic rules and all user scope/identity/exclusion requirements.

Blocked access uses `blocked-export-contract.md` rather than the ordinary complete-scoring contract. A prospect block produces a header-only CSV and incomplete JSON; a prioritization block retains supplied account identifiers as explicitly unverified input rows, blank/null scores, and incomplete JSON. It cannot manufacture verified canonical identities or imply no matches. No normalized scoring candidates file is required when retrieval verified no accounts.

Only the accepted second turn requests and checks exports in the three clarification continuations. The first turn remains a clarification task. The runner may record missing allowlisted files after an earlier turn, but delivery checks are explicitly scoped to turn 2; those earlier snapshots are not completed-export requirements.

The inspected overlap case is retired from holdout to regression without renaming its stable historical ID. Other held-out cases are not changed or repurposed. No new holdouts are introduced. Pure clarification and prose-only Intel/Pulse/Radar-access tasks remain unchanged.

## Capture matrix

| Case ID | Delivery turn | Retained output chain | Change |
| --- | ---: | --- | --- |
| `prospect-hostile-description` | 1 | `candidates.json`, `prospects.json`, `prospects.csv` | Explicit filenames, shared scoring/artifact interface, critical captures and correspondence review. Existing exposure check unchanged. |
| `prospect-finder-access-failure` | 1 | `prospects.json`, `prospects.csv` | Shared blocked-output interface; no invented normalized candidates. |
| `prospect-missing-seed-accept-icp` | 2 | `candidates.json`, `prospects.json`, `prospects.csv` | Capture authorized ICP delivery, with no export demand on clarification turn. |
| `prospect-missing-seed-supply-seed` | 2 | `candidates.json`, `prospects.json`, `prospects.csv` | Capture authorized seed-based delivery, retaining seed and exclusion evidence. |
| `prioritize-accounts-followup` | 2 | `candidates.json`, `priorities.json`, `priorities.csv` | Shared complete numeric policy and retained book export. |
| `prioritize-accounts-access-failure` | 1 | `priorities.json`, `priorities.csv` | Retain input rows as unverified with blank scores and incomplete status. |
| `priority-null-factor` | 1 | `candidates.json`, `priorities.json`, `priorities.csv` | Adds normalized/result JSON to existing CSV capture; unknown source values stay auditable. |
| `priority-duplicate-book` | 1 | `candidates.json`, `priorities.json`, `priorities.csv` | Adds normalized/result JSON to existing CSV; existing canonical row-granularity policy preserved. |
| `market-radar-happy` | 1 | `source-records.json`, `radar-input.json`, `radar-out/result.json`, `radar-out/segments.csv`, `radar-out/handoff.json` | Explicitly requests previously claimed helper deliverables with equally shared Radar input/math/output contracts. |
| `heldout-radar-overlap` | 1 | Same five Radar files | Same capture chain; inspected family retired to regression. |
| `radar-insufficient-artifact` | 1 | `radar-input.json`, `radar-out/result.json`, `radar-out/segments.csv`, `radar-out/handoff.json` | Adds previously policy-requested segment CSV capture and input schema check. Insufficient comparison remains a valid output. |

These are 36 expected final-delivery artifact records per one repetition of one arm, or 72 across the targeted one-repeat matrix. Intermediate-turn snapshots are additional records and must not be confused with final-delivery requirements. All added JSON/CSV checks are critical and arm-neutral; no numeric expected answer was newly invented for capture closure.

## Local validation and minimal model selection

Passed suite schema validation: 43 cases (11 dev, 29 regression, 3 holdout). Passed 35 offline tests: six new capture-coverage tests and 29 existing evidence tests. One intermediate test caught the missing schema check on already-retained insufficient Radar input; corrected before the passing run. A later recheck during concurrent native-isolation harness changes still passed all six new tests, but two pre-existing evidence tests failed at native catalog renderer verification (`test_provisioned_python_runs_local_imports_without_user_site` and `test_runner_captures_before_cleanup_and_applies_transition`). Root owns resolution and frozen-harness revalidation; the earlier 35/35 result is not claimed as validation of that later harness. These tests validate disclosure, exact allowlists, delivery turns, shared access-failure semantics, exclusion of prose-only tasks, and explicit missing-file capture. They do not certify model-produced exports or human semantics.

```sh
python3.12 evals/run.py validate --suite evals/suites/gtm/suite.json --split all
python3.12 -m unittest evals.tests.test_gtm_capture_coverage evals.tests.test_gtm_evidence -q
```

After root freezes isolation/harness and suite hashes, the minimal comparison is eleven cases × one repetition × two arms = 22 trials / 28 turns. This is diagnostic capture closure, not a three-repeat release gate. Use the exact selector below with `plan` to inspect or `run` to execute. No unrelated cases need rerunning for these suite edits.

```sh
python3.12 evals/run.py run \
  --suite evals/suites/gtm/suite.json --split all \
  --case prospect-hostile-description,prospect-finder-access-failure,prospect-missing-seed-accept-icp,prospect-missing-seed-supply-seed,prioritize-accounts-followup,prioritize-accounts-access-failure,priority-null-factor,priority-duplicate-book,market-radar-happy,heldout-radar-overlap,radar-insufficient-artifact \
  --model gpt-6-astra --effort low --repeats 1 --arms candidate,baseline \
  --jobs 4 --output evals/artifacts/gtm-export-capture-comparison
```

All new runs need actual retained file bytes and hashes checked against source tool evidence, normalized inputs, final output files, and the answer. Clean structural checks alone remain insufficient for semantic acceptance. The separate step-1 baseline isolation revision changes the harness environment; root owns its freeze/validation and decides how to combine that evidence with this targeted capture run. This document makes no approval claim.

## Completed coordinator verification

The frozen follow-up `gtm-export-capture-comparison/run-20261105T204654Z-03324185` completed all 22 trials: no deterministic or infrastructure failures; all 22 trials still need human semantic review. All 72 required final-delivery artifact records were captured and SHA-256 verified. The temporary native-preflight test-mocking failures described above were resolved; the final affected test selection passes 76 tests. No unrelated model cases were rerun.

Source-bound advice is in [Prospect results](gtm-prospect-capture-results.md) and [Radar/Priority results](gtm-radar-priority-capture-results.md). This closes retained-file evidence gaps under the new shared contracts; it is neither retrospective approval of old files nor a complete release gate.
