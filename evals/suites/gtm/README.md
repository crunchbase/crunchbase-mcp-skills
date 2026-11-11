# GTM replay corpus

This suite exercises the five GTM skills with fictional companies and inputs. It has 43 cases: 11 development, 29 regression and three held-out scenario families. It is separate from the existing 63-case research corpus and the cross-collection routing suite. A valid corpus and passing offline tests are not completed agent evaluations or release approval.

## Coverage

- Five basic workflows; missing material inputs and actual resumed clarification.
- Resolver-first ordering (including completion before dependent searches), identity ambiguity, conflicting name/domain evidence, CRM export/owner scope, unknown factors, hostile provider descriptions and terminal permission failure.
- Typed JSON/CSV artifact checks, hand-calculated weighted score (50 × .4 + 20 × .3 + 100 × .3 = 56), unknown versus zero, canonical membership and duplicate book handling.
- Account Signals baseline, unchanged repetition, rejected future observation without state advancement, controlled next-day observation and 301-row pagination.
- Industry Insights insufficient-data behavior, complete structured retrieval with 45 companies/36 rounds across three eligible segments, and a separate normalized numerical oracle. Identical peers have seven current/five prior rounds, 20% high-growth share and zero young share: each is steady, with no focus segment. The structured case retains source-records.json and radar-input.json for comparison against actual tool observations and forces multiple pages; the normalized case does not prove retrieval.

Required helper outputs are requested explicitly in user prompts. Prospect Finder and Account Prioritizer happy cases retain normalized candidates.json, the lossless result JSON and the final enriched CSV. Critical semantic review reconciles source tool records → normalized values → scored JSON → final CSV/answer; schema checks alone cannot certify that chain. Numeric-oracle cases include the scoring policy and output interface as shared attachments for both arms, without expected answers; the no-skill baseline is not graded against undisclosed business rules or field names. `run.count` is explicitly an output limit, not a claimed retrieval count. Account Signals state-output contracts and Industry Insights rule/output contracts are likewise supplied to both arms in artifact cases. CSV numbers are compared numerically when the oracle supplies a number; empty cells stay unknown. Row matching is one-to-one. Semantic checks remain pending until an identified person reviews the exact evidence. In a full-retrieval case without injected failure, honest incomplete disclosure is preferable to fabrication but does not satisfy the requested complete result.

## Fixture contract and limits

`base_data.json` is synthetic. Organization, micro-industry, product, similarity, fund, prediction, insight, leadership, product-launch, layoff, address and partnership field IDs were transcribed from the connected metadata inspected November 5, 2026. Declared fixture operators are a bounded replay subset, not a claim that every operator or entitlement was live-verified. Organization card IDs come from the same metadata. All URLs are fictional evidence identifiers and must not be fetched. Current GTM search responses use `{uuid, properties: {...}, value, url?}`, matching live organization/product/round/prediction responses inspected November 5, 2026. `pulse-legacy-flat-envelope` explicitly overrides that shape to exercise historical flat-input compatibility; it is not evidence that the provider currently returns flat rows.

The replay server supports explicit projections, flat AND predicates, supported identifiers, sort/pagination, saved-list state and injected errors. Recursive subqueries remain `UNSUPPORTED_FIXTURE`. Unsupported fields/collections fail explicitly. Do not widen fixture semantics solely to remove a candidate failure; verify the production contract first and document the revision.

Native CRM/calendar tools, host scheduling and delivery are not simulated. CRM CSV inputs exercise normalization/context, not a live CRM connector. These capabilities require separate read-only integration evidence where claimed. Prediction examples are deliberately limited; successful runs do not prove all prediction histories, entitlements or production retrieval quality.

Attachments are frozen inline in each case and staged with hashes. Only their content enters the agent workspace; expected results/rubrics remain in the controller. Allowlisted JSON/CSV outputs (maximum 2 MB each) are retained after every turn, including explicit missing/invalid records. Per-turn fixture snapshots and controlled clock changes are retained. Review digests include the complete artifact content/hashes and state. Retained file/content/hash mismatches invalidate the trial.

Public held-out cases are not secret benchmarks. Keep them separate from instruction tuning. Use new independently authored cases for external readiness claims, and move inspected failures into regression before tuning.

## Run

Use Python 3.11+ (the development interpreter is Python 3.12). Agent workspaces receive the same supported controller interpreter in both arms through `.eval-bin`; user/site imports are disabled and only runtime files are readable beyond the isolated workspace. Run an actual isolated interpreter smoke when changing hosts; an ordinary subprocess unit test does not prove sandbox compatibility.

```sh
python3.12 evals/run.py validate --suite evals/suites/gtm/suite.json --split all
python3.12 evals/run.py plan --suite evals/suites/gtm/suite.json --split all --repeats 3 --arms candidate,baseline
python3.12 evals/run.py run --suite evals/suites/gtm/suite.json --split all --repeats 3 --arms candidate,baseline --jobs 2 --output evals/artifacts/gtm-release-candidate
```

The complete two-arm comparison is 258 trials, plus resumed turns. Pin model and effort before execution. Run development selections first and freeze all source/fixture/harness hashes for the full matrix. Preserve original attempts. The release gate remains the existing strict human gate: full frozen corpus, three repetitions, held-out coverage, all candidate checks passed and adjudicated paired baseline evidence. Automated judgments cannot supply human approval.

The corrected development pilot exposed an inconsistent synthetic Industry Insights enum: 45 records said `operating_status=active` while their fixture contract allowed `operating`. Current source records now use the declared enum, with base-record enum validation preventing recurrence. This is a prospective fixture correction; the frozen pilot remains unchanged and is not treated as clean evidence of ordinary empty-result recovery.

Repair-wave public corpus: 43 cases (11 development, 28 regression, 4 holdouts). The inspected duplicate-book scenario is regression; its independently authored replacement was integrated after candidate freeze with its own embedded fixture. The two added follow-up cases preserve missing named-seed intent before accepting ICP discovery or supplying a seed. See the global evaluator guide for scoped procedural checks and authoritative clock behavior.

Bounded post-audit repair: the inspected conflicting-name/domain Account Brief case retains its ID but is retired to regression; no replacement was authored, leaving a held-out coverage gap. The empty-Account Signals fixture now clears both collection rows and dangling card links plus contradictory current-event summaries. The hostile-description case places the payload in the required seed description and has a controller-only returned-tool exposure check: absence cannot count as demonstrated resistance. Existing frozen runs are preserved; only the three flagged families are targeted for rerun.

## Targeted export-capture closure

The post-R3 capture revision changes eleven existing cases only. Natural Prospect/Priority exports now have exact shared filenames, an equally disclosed scoring/output interface, retained normalized input and final CSV/JSON, and delivery-turn checks. Permission-blocked exports use a separate shared incomplete-output interface so they never require invented verified candidates. Natural Industry Insights happy/overlap retains source pages, normalized input, result, segment CSV and handoff; the already normalized insufficient Industry Insights case additionally retains its policy-requested segment CSV. Clarification and prose-only tasks gain no export requirement.

The `heldout-radar-overlap` case is a regression case despite its historical identifier. Use each case’s declared split when selecting held-out coverage.

### Named-seed follow-up disclosure repair

After human review of the export baseline, `prospect-missing-seed-supply-seed` now explicitly requests forward and reverse similarity coverage in its second user turn. It states that the count is a maximum and that broader category additions require approval. These task requirements are identical for both arms, with no expected company or numeric answer disclosed. Original frozen runs and pending judgments are unchanged; this is a prospective task-contract clarification, not a skill or scoring-code repair. Only this case is selected for the follow-up comparison.

The `priority-null-factor` task now explicitly defines `list_uuids` as the ranked selection of scored output rows, excluding insufficient-evidence and closed rows while preserving the full book in JSON/CSV. An arm-neutral exact-membership check enforces the disclosed rule. This prospective one-case repair leaves old runs unchanged; skill implementation already applies the rule.

The `prospect-missing-seed-accept-icp` shared task now makes closed-company eligibility explicit: retain closed records, but no tier/rank or actionable list membership. A retained numerical score must be described as historical/non-actionable. The CSV oracle checks the known closed row; source-to-JSON review checks actionable membership. This prospective single-case clarification does not change skills or frozen historical outcomes.
