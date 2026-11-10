# GTM skills upgrade and validation report

November 5, 2026. **Implementation delivered; release approval remains pending.** Follow-up review and narrowly scoped evidence-capture/isolation work are recorded in [targeted review](gtm-targeted-review.md) and [export capture review](gtm-export-capture-review.md). The final nine targeted retests completed without deterministic or infrastructure failures. Broad comparisons were stopped at the user's request; no further broad runs are scheduled.

All five downloaded GTM skills are now implemented in the repository on `codex/gtm-skills-upgrade`, as an unpublished 1.1.0 candidate. The five existing research skill trees remain byte-identical to baseline commit `fe4bcf7c20253661d440d88a8bc75d83832ae443`. Installed plugins and published 1.0.3 downloads were not replaced.

## What changed

| Skill | Core workflow retained | Upgrade |
| --- | --- | --- |
| Account Intel | First meetings, follow-ups, seller context, optional CRM history and buyer hypotheses | Canonical identity, sourced facts, structured brief validation, and clarification when supplied name/domain identify different companies |
| Account Pulse | Account events, predictions, priorities, plays, feeds and recurring comparisons | Complete coverage, current/legacy response adapters, deterministic calculations, precise date windows and protected monitoring state |
| Prospect Finder | ICP, segments, look-alikes, mixed pools, exclusions, exports and requested saved-list handoffs | Shared fixed scoring, accepted seeds, explicit mode prerequisites, canonical exclusions and no silent lookalike-to-ICP substitution |
| Prioritize Accounts | Full-book tiers, configurable weights, investor mode, customer evidence and destination exports | Unknown-factor eligibility, validated dates, reproducible scoring, preserved CRM identities and currency |
| Market Radar | Segment direction, territory/account/watch sets, comparisons and prospecting handoffs | Structured records, auditable denominators, fixed rules, minimum sample/peer requirements and explicit insufficient-evidence results |

Original numerical weights remain versioned heuristics. Unknown required inputs do not become zero; predictions do not establish purchasing intent. The standalone packages include their own references, helpers, metadata and notices. Pilot helper schemas/CLI arguments intentionally migrate to documented versioned interfaces.

Concrete repairs include future-date rejection, canonical URL consistency, accepted-seed evidence, duplicate event conflicts, incomplete-coverage restrictions, output-before-state ordering, and currency preservation through CRM ingestion and both scoring exports. Mixed or unknown currencies are never summed. Pulse's N-day window includes exactly N calendar dates; incompatible old state requires an explicit baseline reset.

## Actual validation

| Evidence | Observed result | Interpretation |
| --- | --- | --- |
| Pre-change offline baseline | 131 tests passed | Python 3.12 baseline |
| Final offline checks | **229 tests passed** | Helpers, fixtures, grading, isolation controls, state and output contracts |
| Corrected full GTM comparison | **258/258 completed; zero deterministic or infrastructure failures in either arm** | 43 cases × 2 arms × 3 repetitions; all 258 semantic reviews remain pending; precedes the final targeted identity/fixture repairs |
| Final targeted retest | **9/9 completed; zero deterministic/infra failures** | Three repetitions each: identity conflict, clean empty events and exposed hostile text; semantic review remains pending |
| Corrected research comparison | 105 completion records before user-directed stop | Candidate 36 and previous-version 35: zero deterministic failures; baseline 34: five procedural-check failures; 462 planned trials unfinished |
| Cross-collection development | 12 completed, no deterministic/infra failures | Two deterministic-only passes; ten need review; candidate only, one repetition |
| Packaging | 20 archives, two builds byte-identical | Fourteen CLI help checks and two scoring-library loads succeeded from extracted packages |
| Native discovery | All ten skills discovered by Codex and Claude | Metadata-only project/temporary-plugin checks; no persistent installation or runtime-tool validation |

The research partial results are not a full regression comparison. The full cross-collection and separate ten-case independent challenge campaigns were **not run**, following the user's instruction to limit further testing. The final code changes have targeted evidence rather than a new complete paired matrix. No unfinished or pending item is counted as passed.

The complete GTM run used `gpt-6-astra`, low effort, eight jobs, frozen inputs and three repetitions. Candidate median duration was 50.2 seconds versus 45.2 seconds for baseline. Recorded candidate input/output tokens were 24,358,608/172,778, including 20,509,056 cached input tokens; baseline was 17,257,850/184,521, including 14,351,104 cached input tokens. Cached input is a subset, not an additional total. These figures are host-dependent observations, not dollar costs or approved quality-lift estimates. Interrupted campaigns have incomplete usage accounting.

## Swarm review and final targeted repairs

Workers separately implemented the workflow pair, scoring pair and evaluator; the coordinator implemented Radar and integration. Non-author reviews found defects before the larger comparisons. Fresh-context authors supplied independent challenge families and a replacement held-out case.

The final advisory pass covered all 258 GTM trial outputs and retained artifacts, with deeper source chains per case family and repetition checks. It is machine advice, **not human approval**; reviewer authorship overlaps and inspection limits are recorded in the three advisory reports.

That review found an Account Intel concern despite automated passes: all three candidate repetitions chose the domain-matched company when the supplied name referred to another company. The final instructions now require clarification before briefing, unless returned evidence verifies an alias/rebrand or the user has already resolved the conflict. This inspected held-out case is now regression. There are currently four public holdouts; no new replacement was commissioned after the user narrowed testing.

Two flagged fixtures were also repaired: empty Pulse collections no longer leave stale card references, and the hostile-text case now places its payload in required returned evidence and asserts actual exposure. Earlier non-exposed passes did not establish injection resistance. These three items were the only final model retests. All nine completed without deterministic or infrastructure failures. All three identity-conflict answers now ask which company was intended; all three hostile-text trials pass the returned-payload exposure check and the no-write check. Human labels remain pending.

## Evaluator improvements and preserved failures

The evaluator now stages identical shared contracts for both arms, retains JSON/CSV/state before workspace cleanup, verifies hashes, supports controlled multi-turn changes and preserves missing/invalid artifacts. Internal skill procedures can be explicitly candidate-only; excluded checks are recorded as `not_applicable`, not passed. Substantive safety, identity and outcome checks remain applicable to both arms.

Early runs exposed an unusable isolated Python runtime, weak ambiguity data, contradictory clock instructions and undisclosed artifact contracts. Repairs were prospective; no frozen failure was relabeled as a pass. The first full GTM run's two candidate and sixteen baseline failures remain in its original report, with confounds documented. Those counts are not comparable quality rates across revised contracts. An earlier research campaign was stopped with 37 completion records when those defects were identified.

The saved September research run also still records failures, an infrastructure error and pending human judgments. It was a useful standard for repetition and review discipline, not evidence of completed human approval in the inspected local artifacts.

## Live and integration evidence

Read-only live checks inspected required collection/field/card contracts and actual nested response envelopes. For the resolved Crunchbase organization, all four product pages yielded seven unique records and all three funding-round pages yielded five. Both scoring helpers produced 55 from the same normalized live input. Pulse normalized all five live funding rows and one prediction without dropping records. These are narrow compatibility checks, not complete entitlement or production-workflow coverage.

A synthetic Radar → Prospect → Prioritize → Pulse helper chain preserved canonical IDs, exclusions, unknown scores and date boundaries. Explicit normalization was required; Pulse may need additional growth-tier evidence and therefore leave an otherwise scored prospect unranked. Original market scope and consent were retained separately. This does not prove autonomous orchestration, live CRM import or recurring-host execution.

Codex 0.166.0-alpha.5.1 and Claude Code 2.1.220 discovered all ten skills without model calls or installed configuration changes. Codex evidence covers project skills; Claude covers its temporary inline plugin loader. These checks preceded the last Intel wording repair; metadata structure is unchanged. Claude.ai upload, persistent plugin installation, native CRM/calendar workflows and real scheduling remain unverified. No production lists, CRM records, schedules or messages were changed.

## Targeted follow-up: review and capture isolation

At the user's request, the follow-up covers the nine final targeted results and the specific export/isolation gaps only. Evidence review supports the three intended repairs; it also exposes projection-dependent prospect scoring, described below. The coordinator independently cross-checked the Intel reviewer’s conclusions against all three source traces and final answers. These remain agent findings, not human labels.

The isolation repair explicitly disables the discovered native catalog, with a positive canary and fail-closed verification before model work. Metadata-only rendering retains all ten intended candidate names/paths and the exact injected instructions; baseline retains neither candidate nor native skill catalog entries. Historical ambient exposure is preserved as a limitation. This proof concerns the local CLI renderer, not a remote request capture.

Seventy-six targeted offline tests pass across the affected runner, evidence capture and new capture-coverage tests. The eleven-case follow-up uses one repetition in each arm (22 trials/28 maximum turns), solely for diagnostic capture closure. Newly explicit filenames/schemas are shared with both arms and apply prospectively; old outputs are not failed retroactively. The inspected Radar overlap case is retired to regression, leaving three GTM holdouts. Skills and packaged artifacts are unchanged by this follow-up.

**Completed result:** 22/22 trials, zero deterministic failures and zero infrastructure failures; all 22 still require human semantic adjudication. All 72 expected final-delivery artifact records were captured and hash-verified. Initial missing snapshots on clarification turns are not missing delivery files. The baseline trace audit covers 11 trials, 14 turn traces and 33 shell-command attempts: no host-skill path attempts or inaccessible-skill claims were observed. This supports the bounded repair, not a guarantee about future hosts or runs.

Review found no new candidate source-to-export inconsistency in these captures. Prospect JSON/CSV rows agree throughout; Radar/Priority source counts and independently recomputed math agree. Baseline category expansion, closed-account treatment, unscored handoff membership and several underspecified field/tie conventions are recorded as semantic differences or contract ambiguities, not silently converted to passes or newly invented deterministic failures. At capture-closure time the earlier prospect growth-projection inconsistency remained unresolved; the subsequent three-repeat repair is recorded below.

Evidence: [22-trial report](../evals/artifacts/gtm-export-capture-comparison/run-20261105T204654Z-03324185/report.md), [22 review packets](../evals/artifacts/gtm-export-capture-review/), [Prospect review](gtm-prospect-capture-results.md), [Radar/Priority review](gtm-radar-priority-capture-results.md), [native isolation proof](../evals/artifacts/gtm-upgrade-evidence/next-review/isolation/README.md), and [actual baseline trace audit](../evals/artifacts/gtm-upgrade-evidence/next-review/isolation/actual-run-baseline-path-audit.md).

## Growth retrieval standardization follow-up

The user authorized the next growth-field repair. Prospect Finder and Prioritize Accounts now require both live-supported organization growth fields for positive-weight growth scoring, retain both values, and permit a single-measurement fallback only with evidence of unavailability. Omitted projections no longer qualify as missing data. Zero growth weights and supplied/no-requery evidence keep their existing boundaries. The formula and helper scripts are unchanged.

Only the previously inconsistent Prospect case was rerun: three candidate repetitions, zero deterministic or infrastructure failures. The same canonical account scored **81/81/81**, with returned numeric growth 79 and tier 70 normalized in every repetition and matching JSON/CSV values. All 9 output files were retained and hash-verified. 20 existing scoring tests pass; both skill validators pass. One repetition used the existing optional broader-match fill and returned three rows rather than one, so this establishes consistent scoring for the same account, not identical discovery populations. Unsupported/missing-field fallback and Prioritize were not newly model-tested; broader release approval remains pending.

[Detailed review](gtm-growth-standardization.md), [three-trial report](../evals/artifacts/gtm-growth-standardized/run-20261105T210534Z-280e3984/report.md), and [updated packages](../dist/1.1.0-gtm-growth-standardized/). The new package set supersedes the earlier candidate archive set; only the two scoring skills changed, and two builds are byte-identical.

## Remaining release concerns and next steps

1. **Adjudicate the semantic evidence.** Review the full-run packets plus final targeted results, particularly identity handling, market claims, scope, prediction interpretation and permission-error behavior. Agent advice cannot populate human approval fields.
2. **Resolve comparison/coverage limitations before claiming quality lift.** Thirteen baseline host-skill path attempts returned denied or empty results; no skill contents were observed. A subsequent metadata-only prompt inspection confirmed installed skill names remained visible despite the discovery-skip flag. Earlier comparisons therefore have ambient catalog exposure; they are not a clean no-skill baseline. Earlier natural export cases lacked retained final bytes; the bounded eleven-case follow-up now explicitly captures the disclosed outputs, with results recorded separately. The earlier 301-record baseline uses a provenance key that differs from the shared interface; that separate historical interface concern is not retested by the export follow-up. Review these as limitations, not silently approved behavior.
3. **Keep optional integrations accurately scoped.** Native CRM/calendar, actual destination imports, recurring delivery and live entitlement combinations need separate evidence where release claims require them.
4. **Choose the release gate deliberately.** The repository's existing gate requires a complete current frozen comparison and independent human semantic/live-coverage sign-off. The user has deferred broad reruns. This work therefore supports targeted review of the updated candidate, not an assertion that the full release gate has passed. No further broad run is scheduled.

That candidate repair is now implemented and narrowly verified as described above: supported growth projections are consistent before scoring, with explicit unavailability required for fallback. The nine-trial evidence review found projection-dependent prospect scores (83/81/83): some repetitions requested both growth measurements, others only one. The arithmetic is consistent with each input, but retrieval consistency remains a concrete production concern. No scoring policy repair or new release approval is implied by capture-only follow-ups.

If another code repair follows review, test the affected scenario and preserve its prior result. Any inspected holdout used for tuning must be retired. Broader release recertification is a separate next step when requested.

## Deliverables and evidence

- [Current candidate archives and checksums](../dist/1.1.0-gtm-growth-standardized/)
- [Workflow guide](guides/gtm-workflows.md) and [draft release notes](gtm-release-notes.md)
- [Corrected full GTM report](../evals/artifacts/gtm-full-comparison-r3/run-20261105T195955Z-0edf0e6a/report.md)
- [258 human-review packets](../evals/artifacts/gtm-r3-review/)
- [Final targeted report](../evals/artifacts/gtm-targeted-final/run-20261105T203410Z-7abd93e9/report.md) and [nine targeted review packets](../evals/artifacts/gtm-targeted-final-review/)
- [Intel/Pulse advisory](../evals/artifacts/gtm-upgrade-evidence/r3-advisory/intel-pulse.md), [Radar/Prioritize advisory](../evals/artifacts/gtm-upgrade-evidence/r3-advisory/radar-prioritize.md), [Prospect advisory](../evals/artifacts/gtm-upgrade-evidence/r3-advisory/prospect.md)
- [Partial research analysis](../evals/artifacts/gtm-upgrade-evidence/research-r3-partial-analysis.json)
- [Native discovery](../evals/artifacts/gtm-upgrade-evidence/native-hosts-r3/README.md), [helper-chain evidence](../evals/artifacts/gtm-upgrade-evidence/handoff-chain/verification.json), and [full provenance/evidence directory](../evals/artifacts/gtm-upgrade-evidence/)
- [Prior assessment](gtm-skills-upgrade-plan.md), [execution plan](gtm-swarm-execution-plan.md), and [repository methodology](../evals/METHODOLOGY.md)

Raw evidence, review packets and archives are ignored by Git. Preserve them separately with the source checkout; source ZIP hashes and frozen implementation/harness snapshots are retained in the evidence directory. Nothing has been published or merged.

## User signoff on the growth retest

Victor approved all three presented growth-retest cases, both judgments each: **3/3 cases, 6/6 judgments passed**. Explicit approvals and evidence-bound labels are preserved in `evals/artifacts/gtm-growth-standardized-review/human-labels-step3.json`; earlier review steps remain intact. This was assistant-assisted, unblinded chat review with recommendations shown before approval, not independent calibration. The approval covers this targeted growth repair only; the full release gate remains unmet. Future review cases should include an accompanying recommendation and still await the user’s judgment.

## User signoff on the nine targeted behavior cases

Victor explicitly approved all nine cases individually after evidence summaries and recommendations: **9/9 judgments approved**. Evidence-bound labels and prior steps are preserved in `evals/artifacts/gtm-targeted-final-review/human-labels-step9.json`. This was assistant-assisted, unblinded review, not independent calibration. Hostile-text approvals retain the disclosed limitations: old exports were not retained, and two historical scores 83 preceded the standardized 81. These approvals do not validate those missing exports or the superseded scoring approach. Presentation and query-efficiency caveats remain documented.

Together with the separately approved growth retest, **12 review items / 15 judgments are approved**. The export-capture batch still has 22 items / 46 judgments pending. No full release approval is implied.

## Named-seed follow-up: prospective task-contract repair

During export review item 7, the user requested a fix and retest of only that case. The no-skill baseline had returned a direct similarity card but omitted reverse investigation and expanded to a category pool. The graded forward/reverse requirement was not explicit in its task prompt. Only `prospect-missing-seed-supply-seed` was revised: both arms now receive explicit bidirectional retrieval/coverage, maximum-not-quota count, and approval before broader category additions. No skills, scoring code, fixtures, installed configuration, or historical results changed.

One paired retest completed (two trials/four turns), with no deterministic or infrastructure failures. Both arms asked for the missing seed, then retrieved one forward/zero reverse matches, excluded the seed, made no category additions or external writes, and exported one Brambleflux result at 81/A. All six final files captured/hash-verified; six targeted capture-coverage tests and suite validation passed. This is a clarified-task diagnostic, not an unchanged benchmark rerun or a full release gate. Both new packets and original item 7 judgments remain pending explicit human review.

See [source-bound retest review](gtm-seed-followup-retest.md) and `evals/artifacts/gtm-seed-followup-repair/run-20261105T223742Z-69549722`.

## Missing-factor actionable-selection clarification

The user passed original export item 9 with its documented shared-contract ambiguity and requested only that case be retested. Shared instructions now explicitly restrict `list_uuids` to scored output rows while preserving unscored accounts in the full export. Both candidate and baseline meet the new exact-membership check; all six files are verified, with no deterministic/infrastructure failures across two trials. Skill code is unchanged. New semantic labels remain pending; see [bounded retest](gtm-selection-contract-retest.md).

## Delegated review completion

The user authorized autonomous continuation on recommended passes. All 22 export-review items now have dispositions: 10 individual approvals, 10 delegated passes (including skipped item 4), and 2 preserved historical exceptions addressed by prospective task-contract retests. Closed-company eligibility retest succeeds on source/output evidence and a corrected eight-row CSV check; the original erroneous one-row check report remains intact. No further material skill defect was identified, and no skill code changed. Delegated decisions are separately labeled as agent review, not independent human judgments. See [completion record](gtm-delegated-review-completion.md). Full release readiness is not implied.
