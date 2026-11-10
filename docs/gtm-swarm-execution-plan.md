# GTM implementation and evaluation swarm plan

Plan dated November 5, 2026. **Execution scope was later narrowed by the user to targeted retests; the final validation report records completed and deferred work.** This is the execution companion to the [GTM assessment](gtm-skills-upgrade-plan.md). It covers upgrading all five GTM skills, extending the existing evaluator, protecting the five research skills, and preparing a tested release candidate. Implementation started on November 5; see [execution status](gtm-implementation-status.md) for actual progress.

The swarm should carry implementation, debugging, automated evaluations, read-only integration checks, and review preparation to completion without routine approval pauses. It must preserve the repository's distinction between automated evidence and human release approval. Agents cannot supply human labels or declare an unreviewed candidate release-ready.

## Previous testing inspected

| Evidence | Verified state | Implication for this work |
| --- | --- | --- |
| Current research corpus | 63 cases: 27 development, 28 regression, 8 held-out | Preserve and rerun it with all ten skill descriptions available. |
| Current offline checks | 131 tests passed on November 5 using Python 3.12; all 63 cases validated; version check reported 1.0.3 | Establish this as the pre-change baseline. CI must continue passing. |
| September 30 full evaluation | 60 frozen cases × two arms × three repetitions = 360 trials | Retain matched candidate/no-skill comparisons and repetition, not only happy-path smoke tests. |
| That run's recorded candidate results | 3 failed, 176 needing review, 1 infrastructure error out of 180 trials | Historical artifacts are diagnostic evidence, not a completed release approval. |
| That run's recorded baseline results | 45 failed and 135 needing review out of 180 trials | Do not derive an approved quality-lift claim from unadjudicated results. |
| Existing release gate | Full frozen suite, at least three repetitions, held-out coverage, all candidate checks passing, fully adjudicated paired baseline evidence | Apply the same gate to GTM and research regressions. No “Pass*” for unknown judgments. |
| Existing CI | Version synchronization, suite validation, offline tests on Python 3.11 | Extend it explicitly to each new suite; the default validation command only selects research. |

The full run's [report](../evals/artifacts/full-evaluation/run-20260930T224500Z-d1942f26/report.md) is an ignored local artifact and will not travel with the repository. Its counts belong to the frozen September suite, not today's revised 63-case corpus. The October revision retired inspected holdouts into regression and added recovery cases; do not describe the remaining public holdouts as sealed independent evidence.

That run retained 359 completed trials and one infrastructure error, with 395 judgment fields still null across 359 review packets. All five saved run summaries inspected were `not_ready`. Historical model-advice summaries are explicitly exploratory, not human approval. The old model/host settings are provenance, not a reason to change the current execution model without recording the choice.

The initial test attempt used the machine's default Python 3.9 and encountered two import errors because the evaluator requires Python 3.11+. Repeating under the installed Python 3.12 passed all 131 tests. Pin a supported interpreter in the execution runbook.

## Swarm organization

Use at most four active agents: one coordinator and three workers. Give workers exclusive file ownership; rotate responsibilities between waves instead of exceeding capacity. No worker may merge its own implementation into the acceptance result without a separate review.

| Role | Ownership | Required handoff |
| --- | --- | --- |
| Coordinator | Shared contracts, task ledger, integration, requirements/catalog/release docs, run scheduling | Frozen decisions, file ownership, integrated revision, evidence index, unresolved issues |
| Workflow worker | Account Brief and Account Signals, then Industry Insights | Source changes, dependency matrix, targeted checks, limitations, review notes |
| Scoring worker | Prospect Finder and Account Prioritizer; common scoring and CRM normalization | Versioned input/output schemas, shared scoring policy, independently testable examples, parity checks |
| Evaluation worker | Harness, synthetic fixtures, artifact grading, test suites, CI | Tested fixture capabilities, independently specified expected outcomes, frozen cases and run commands |

During independent review, reassign an agent that did not author the component. Have a fresh-context reviewer author held-out scenario families without receiving implementation traces or development failures. Holdouts remain outside implementation workspaces until evaluation. Agent-authored review and judge advice remain machine evidence, regardless of whether a separate agent produced them.

## Work waves and dependencies

### Wave 0 — Establish the baseline and contracts

1. Record source ZIP hashes, current commit, clean/dirty working-tree state, Python and host versions, tool availability, and the baseline checks above. Preserve unrelated user work. Use an isolated `codex/` implementation branch or checkout where appropriate.
2. Create a task ledger with owner, exclusive paths, dependencies, acceptance checks, revision, evidence path, and status for each task. Keep raw runs in ignored `evals/artifacts/`; keep public fixtures synthetic.
3. Freeze shared decisions before implementation: explicit Crunchbase activation; material scope clarification; resolver-first identity; unknown-data eligibility; supported predictions/events; CRM read-only; list-write reconciliation; state lifecycle; host capability fallbacks.
4. Retain the existing numerical weights as a versioned heuristic, but make insufficient-evidence behavior explicit. Define valid normalized dates, money, identifiers, scores, and provenance. Define seller context, CSV/JSON outputs, Industry Insights handoff, and recurring-state schemas.

**Exit:** every skill has an observable outcome, supported capabilities, adjacent-task exclusions, and testable schemas. Routine implementation choices use these contracts rather than reopening product questions.

### Wave 1 — Build the harness while porting core workflows

- Workflow worker ports Account Brief using production resolution/query/output patterns; tests first meetings, follow-ups, optional CRM, and missing seller context.
- Scoring worker ports Account Prioritizer and Prospect Finder together; fixes future dates, unknowns, identity/exclusion handling, and score parity.
- Evaluation worker extends replay and artifact support, beginning with independently specified calculator and failure cases. It does not copy implementation formulas as its oracle.
- Coordinator integrates common references and dependency documentation, verifies live tool schemas read-only where available, and resolves shared-file edits centrally.

**Exit:** one end-to-end Account Brief replay and paired scoring workflows execute against synthetic data; deterministic checks pass; generated files are captured and graded.

### Wave 2 — Monitoring, segment analysis, and independent review

- Workflow worker ports Account Signals, including complete pagination, prediction histories, ranked outputs, and transactional state updates.
- Scoring worker moves to Industry Insights after scoring integration: replace expert answers with structured retrieval and auditable aggregation; preserve segment labels and territory handoffs with correct denominators.
- Evaluation worker builds monitoring transitions, Industry Insights scenarios, CRM cases, all-ten-skill routing, and failure injection.
- Coordinator reviews the earlier components, then rotates a non-author worker into adversarial review. Test Industry Insights → Prospect Finder → Prioritize → Account Signals handoffs with canonical IDs, preserved scope, and schema versions.

**Exit:** all five workflows execute in replay, all P0/P1 findings are resolved or explicitly block the candidate, and no feature is advertised beyond tested capabilities.

### Wave 3 — Development testing and repair

Run offline checks first, then selected development replays, then development plus regression cases. Classify each failure as implementation, fixture fidelity, grading, environment, or genuine missing capability. Fix the cause, add the regression, and rerun the affected checks before broadening.

Never change thresholds merely to make a run pass. A legitimate contract or grader correction requires a new version, rationale, and preserved old evidence. Do not run full matrices repeatedly while known deterministic failures remain. Retain failed attempts; an infrastructure retry is a linked new attempt, not replacement evidence.

If a fix leaves the same failure unresolved, assign a fresh worker to diagnose it with a new hypothesis. Separate swarm concurrency from evaluation-runner concurrency: begin with two replay jobs and run campaigns sequentially if overlapping runs would distort latency or exhaust capacity.

**Exit:** integrated source and evaluation contracts are stable, development/regression outcomes are reviewed by a non-author agent, and the full evaluation workload is frozen.

### Wave 4 — Frozen comparisons and review preparation

Evaluate the current ten-skill candidate against a no-skill baseline using identical user turns, fixtures, clock, host/model settings, concurrency, and limits. Run at least three repetitions per case. Also compare the five existing research workflows against the pre-change five-skill tree using the supported `previous` arm, so regressions from new routing descriptions are observable.

Run the existing research corpus, a new GTM corpus, and cross-collection routing/handoff coverage. Choose case count from the coverage matrix, not an arbitrary target. The existing research comparison alone is 378 trials; a GTM corpus of N cases adds 6N trials, plus separately defined cross-collection cases and any previous-version arm. Print and archive the exact job plan before execution. Pin model/effort and record token use and latency; do not present historical costs as a new estimate.

Export shuffled review packets containing full user-visible turns, tool observations, persisted state, and generated artifacts. Optional independent-model judgments may triage issues but cannot satisfy the human-review gate. If a holdout result informs a repair, retire that case into regression and commission a fresh held-out family before claiming new held-out evidence.

Any source, fixture, or harness change after the freeze requires a new frozen revision and the complete required release comparison. Old transcript-bound reviews do not transfer to changed evidence. Critical or disputed human judgments receive a second human review. Baseline failures are allowed; pending or infrastructure outcomes are not. Positive measured lift is not itself required by the current gate.

**Exit:** every planned trial is accounted for, deterministic and infrastructure outcomes are known, review packets are complete, and all pending human judgments are explicit.

### Wave 5 — Live checks and release candidate

Run separate read-only live checks for identity, schema/operator contracts, actual response envelopes, required collections, optional-field behavior, and representative entitlements available to the account. Record untestable entitlement states as gaps; do not simulate them and call them live-verified. Exercise CRM/calendar read capabilities only for supported, scoped examples; use synthetic CRM exports for broader automated coverage. Production list changes, CRM mutations, message sends, and schedule creation are not required for this test plan.

Verify standalone packages, bundled references/helpers, notices, metadata, version consistency, and representative Codex/Claude discovery. Use isolated runtime copies rather than replacing the user's installed skills. Add a GTM workflow guide and update the catalog only for implemented and validated behavior. Prepare archives/checksums and a release description; publication is a separate authorized step.

**Exit:** a review-ready release candidate with all automated results, live compatibility evidence, known gaps, and human review packets. Release-ready status additionally requires the existing human semantic and live/coverage sign-off.

## Required evaluator extensions

These are implementation tasks, not capabilities already established by the research evaluator:

1. **GTM provider contracts:** add synthetic records and validated contracts for the required micro-categories, products, similarities, funds, prediction histories, insights, and account-event collections. Unsupported fixture constructs remain explicit coverage failures.
2. **Case attachments:** stage per-case CRM CSVs, seller context, exclusions, and prior-state files with safe relative paths and frozen hashes. Keep answer keys and rubrics outside the agent workspace.
3. **Artifact capture:** retain approved CSV/JSON outputs and local state before temporary workspaces disappear. Grade contents, canonical membership, types, scores, coverage, and schema versions; file existence alone is insufficient.
4. **Evidence binding:** include artifact and state hashes in semantic-review evidence so stale labels cannot approve a changed result. Missing artifacts fail or remain pending; none disappear from the denominator.
5. **Time and state transitions:** support successive runs with controlled clocks and fixture changes, interruption, replay, changed scope, and idempotency. Distinguish an event's date from when it was first observed.
6. **CRM and host adapters:** add narrow read-only synthetic CRM tools where claimed; instrument forbidden writes. Keep prompt construction, recurring execution, and actual host scheduling as separate capabilities.
7. **CI integration:** validate every suite, run all helper/fixture/grader tests, and verify independently installable packages. Keep model and live evaluations outside ordinary offline CI.

## Test matrix

| Area | Required cases |
| --- | --- |
| Selection and dialogue | Positive/negative routing across ten skills; missing inputs; accepted defaults; follow-ups; ambiguous identity; no repeated clarification |
| Scoring | Unknown versus zero; minimum coverage; invalid/finite numeric inputs; weight and tier boundaries; deterministic ties; score parity; date boundaries, leap days, future events |
| Retrieval | Empty results; 301 records with a 300-row first page; UUID deduplication; partial retrieval; bounded recovery; authorization, usage-limit, and service errors |
| CRM and files | Exact identity, duplicate CRM accounts, owner filters, won/lost history, exclusions, missing domains, CSV escaping, hostile cell/text content, provenance |
| Monitoring | First baseline, unchanged run, new signal, prediction transition, duplicate alert prevention, failed run, changed book/rubric, corrupted state |
| Industry Insights | Complete denominator, overlapping segments, sparse samples, unknown versus zero, fixed direction boundaries, source disagreement, valid prospect handoff |
| Writes and hostile content | No unrequested mutations; preview before authorized fixture writes; persisted membership; uncertain/partial writes; hostile records cannot alter authority |
| Outputs | Correct files and canonical IDs; as-of date and scope; source links; material limitations; hypothesis versus fact; no buying intent inferred from funding predictions |
| Evaluator integrity | Missing/malformed grades, missing trials, changed rubrics/artifacts, unknown checks, pending semantics, and model labels cannot yield release approval |

## Runbook and completion rules

Use the installed supported interpreter for the initial baseline:

```sh
python3.12 scripts/sync_version.py --check
python3.12 evals/run.py validate --split all
python3.12 -m unittest discover -s evals/tests -v
```

After the new suite exists, validate it and inspect its workload explicitly:

```sh
python3.12 evals/run.py validate --suite evals/suites/gtm/suite.json --split all
python3.12 evals/run.py plan --suite evals/suites/gtm/suite.json --split all --repeats 3 --arms candidate,baseline
python3.12 evals/run.py run --suite evals/suites/gtm/suite.json --split all --repeats 3 --arms candidate,baseline --jobs 2 --output evals/artifacts/gtm-release-candidate
```

Resolve and freeze the model settings before the run. Use the unique returned run directory with `evals/grade.py` and `evals/review.py export`; retain their outputs. A nonzero grading exit due to pending semantics is an unfinished review gate, not a reason to weaken the grader. Apply the same commands to the research suite and the chosen cross-collection suite. Run-directory names must be fresh; never overwrite historical artifacts.

The coordinator continues through reversible implementation, testing, fixes, and documentation. Pause only dependent work when a real blocker requires unavailable credentials/capabilities, a material unresolved product decision, an explicit spending limit, or human judgment. Continue unaffected work and provide the exact blocked item and evidence. Do not retry terminal access or usage-limit errors indefinitely, fabricate approval, or publish an unreviewed release.

The final evidence index must identify revisions and hashes; suites and job counts; offline and replay outcomes; baseline/previous comparisons; token/latency results; live checks; artifact paths; package checksums; unresolved defects; and pending human judgments. Report separately: **implementation complete**, **automated validation complete**, **review-ready**, and **release-approved**.

The human boundary comes from the existing [evaluation methodology](../evals/METHODOLOGY.md): “A model judge must differ from the candidate model” and “Its proposed labels are stored separately and cannot satisfy the release gate.” The [corpus instructions](../evals/suites/private-company-research/README.md) also require “explicit independent human review.” The swarm can autonomously prepare all evidence and fixes; preserving this standard means leaving those human judgments pending until a person supplies them.
