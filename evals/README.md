# Crunchbase skill evaluations

This is a repository-wide evaluation framework. The default suite covers the five skills in the private-company research collection. Separate [GTM](suites/gtm/README.md) and [cross-collection](suites/cross-collection/README.md) suites exercise the five GTM skills and routing across all ten; select each explicitly with `--suite`. The evaluator is development infrastructure, not an instruction file that users must install with a skill.

The framework runs a real agent against a local, stateful MCP fixture. It compares the current skills with the same agent and tools **without skills**, records actual tool effects, and leaves judgment-dependent checks pending until reviewed. It never connects to production Crunchbase or changes production saved lists.

## Requirements

- Python 3.11 or newer; the harness and offline tests use the standard library.
- An authenticated Codex CLI for behavioral runs. The current isolation preflight was exercised with `0.166.0-alpha.5.1`; permission profiles, `debug prompt-input`, and per-name `skills.config` disables are required. Unsupported or unverifiable native-catalog isolation fails before model evaluation. Recheck compatibility when upgrading.
- A model and reasoning effort, either explicitly supplied or resolved once from the local Codex configuration. The chosen settings are pinned in the run manifest.

## Quick start

From the repository root:

```sh
# No model calls or production services.
python3 -m unittest discover -s evals/tests -v
python3 evals/run.py validate

# Inspect the exact workload before spending inference tokens.
python3 evals/run.py plan --split all --repeats 3 --arms candidate,baseline

# Execute a frozen candidate/no-skill comparison.
python3 evals/run.py run --split all --repeats 3 --arms candidate,baseline \
  --jobs 2 --output evals/artifacts/release-candidate

# Automatic grading; exit 1 means the release gate is not satisfied.
python3 evals/grade.py --run evals/artifacts/release-candidate/RUN_DIRECTORY
```

Replace `RUN_DIRECTORY` with the unique `run-...` directory printed by the runner. `--output` names its parent directory. Use `run.py --help` for case, split, model, timeout, and previous-version options. The default selection is development and regression; `--split all` explicitly includes held-out cases. The complete 63-case comparison with two arms and three repetitions is 378 trials, plus resumed turns. Start with selected development cases to check the environment before a full run. Keep seeds, concurrency, tool contracts, timeouts, and model settings matched across comparison arms. Each invocation creates a new directory and preserves previous attempts.

The report separates failures, infrastructure errors, and checks needing review. An exit code of zero from an agent process is not a successful outcome. The release gate requires the complete suite, three or more repetitions, held-out coverage, every candidate check passing, and adjudicated paired baseline results. This initial conservative policy can be revised prospectively with documented product requirements; do not move its threshold after seeing a result.

## Human review and optional model advice

```sh
python3 evals/review.py export --run evals/artifacts/release-candidate/RUN_DIRECTORY \
  --output evals/artifacts/review-01
```

Give a reviewer `packets.json` and `instructions.md`, keeping `private-map.json` and run metadata private. Packets are shuffled and omit arm/case labels. Reviewers fill each `judgments` entry with `true`, `false`, or `null` and cite evidence. Null remains pending. Output content itself may reveal the skill, so blinding reduces bias without guaranteeing anonymity.

```sh
python3 evals/review.py import --packets evals/artifacts/review-01/packets.json \
  --mapping evals/artifacts/review-01/private-map.json \
  --reviewer "Reviewer name" --output evals/artifacts/human-labels-01.json
python3 evals/grade.py --run evals/artifacts/release-candidate/RUN_DIRECTORY \
  --reviews evals/artifacts/human-labels-01.json
```

An optional independent model can suggest labels. Supply the actual candidate model and a different judge model supported by your host:

```sh
python3 evals/judge.py --packets evals/artifacts/review-01/packets.json \
  --candidate-model CANDIDATE_MODEL --model DIFFERENT_JUDGE_MODEL \
  --output evals/artifacts/judge-01
python3 evals/review.py calibrate --human evals/artifacts/review-01/packets.json \
  --model evals/artifacts/judge-01/suggestions.json
```

Judge suggestions cannot approve a release. Independently label representative passes **and failures** before inspecting suggestions, then inspect false-pass rates and disagreements. The calibration report includes agreement, a confusion matrix, Cohen's kappa, and descriptive intervals. Critical failures and disputed labels should receive a second human review. The independent-model requirement reduces shared bias; it does not establish judge accuracy.

## What is measured

- **Routing:** observed skill reads for appropriate requests and avoidance for unrelated requests. Activation is inferred from successful file-read traces and matching content, not an operating-system audit of every file access; opaque reads remain unknown. Baseline runs are excluded from skill-activation scoring. The generated catalog tests selection behavior, while actual plugin discovery is verified separately.
- **Clarification:** missing material inputs, one bundled question, accepted defaults, ambiguity resolution, and genuine resumed conversations.
- **Task outcomes:** preserved scope, factual grounding, financial denominators, uncertainty, complete pagination when requested, and correct persisted list membership.
- **Failure behavior:** authentication, metering, validation, transient errors, partial writes, unsupported operations, and hostile text embedded in returned data.
- **Reliability and cost proxies:** repeated case success, observed all-repetitions-pass rates, tokens, cached tokens, latency, and paired quality changes with scenario-family bootstrap intervals where justified.
- **Calculator integrity:** independent numeric examples, date boundaries, malformed inputs, unknown versus zero values, deduplication, permutation invariance, and scale invariance.

## Artifacts and privacy

Runs retain the frozen suite, skill/fixture/harness hashes, exact job plan, model settings, CLI version, prompts, raw event traces, tool arguments/results, state snapshots, stderr, usage, and review evidence. Keep raw runs in ignored `evals/artifacts/` or outside the repository. Do not publish real customer records, list names, credentials, or private production transcripts.

The fixture uses fictional companies and synthetic financial data. It implements a declared subset of Crunchbase tools and rejects unsupported constructs. Passing replay tests does not prove production connector availability, entitlements, production retrieval quality, or compatibility with another agent host. Before release, perform a separately documented read-only live integration check with approved examples. Production writes are never part of automated replay testing.

The older walkthroughs used partial fixtures and explicit skill invocation. They are diagnostic evidence only, separate from this suite's routing and baseline measurements. See [methodology](METHODOLOGY.md) for research sources, experimental controls, limitations, and the legacy migration rationale.

## Add another suite

Create a directory under `evals/suites/` with a versioned `suite.json`, fixture data, and documentation. Each case supplies a natural user request, a scenario-family split, a fixture configuration, and outcome checks. Keep expected answers outside the agent workspace. Use `semantic` checks for meanings that cannot be established reliably by code; do not replace reasoning with fragile keyword matching. Add meaningful tests for fixture/grader behavior and make validation reject unknown fields/check kinds.

Run development cases while editing. Keep regression cases stable and held-out scenario families untouched during tuning. Public holdouts are an organizational boundary, not secret benchmarks; important release claims should also use independently authored, sealed cases supplied with `--suite`. Freeze or revise those cases before evaluating, never in response to one candidate's score.

### Runtime discovery and call budgets

`max_calls` counts task calls, including failed attempts. Completed built-in `codex` resource/resource-template inventory calls are excluded only when their arguments are empty or target the replay server and their result is exactly an empty inventory. Nonempty results, errors, other servers, and other tools still count. Inventories remain in raw evidence and explicit tool checks.


### Attached inputs, outputs and controlled transitions

Cases may provide `attachments: [{path, content}]` and `artifacts: [{path, format}]`, where format is `json` or `csv`. Paths are confined relative paths; instructions, skills and `.eval-bin` cannot be overwritten. Attachments are UTF-8, frozen with the case and hash-recorded in the trial. Captures preserve raw bytes, SHA-256, parsed content and missing/invalid status after each turn. Files are limited to 2 MB. JSON rejects nonfinite numbers; CSV accepts UTF-8 BOM, rejects malformed widths/duplicate headers and preserves blank numeric values.

`artifact_json` checks typed structural subsets; lists are ordered and exact length. `artifact_csv` checks required columns, optional exact unique key membership, and optional one-to-one row subsets (finite numerical expectations compare numerically). `artifact_unchanged` compares a captured path's hash between explicit `from_turn` and later `turn`. Declare every checked path in `artifacts`. Artifact contents/state are included in semantic-review digests and review packets; changed retained bytes or parsed values invalidate evidence. None of these deterministic checks proves prose grounding without review.

`fixture_updates: [{turn, fixture, as_of}]` can replace allowed fixture components before a subsequent resumed turn, with an optional controlled date. Inputs/outputs and provider list state persist in the same isolated workspace; each turn freezes its effective fixture. These are scripted controlled transitions, not an autonomous scheduler or an arbitrary user simulation.

### Agent Python runtime

Both comparison arms receive identical `.eval-bin/python`, `python3`, and versioned wrappers around the resolved controller interpreter, with `-E -s -S` to ignore inherited Python settings and user/site startup code while retaining local helper imports. The filesystem allowlist includes the interpreter prefix and actual required non-system runtime libraries; controller inputs/outputs remain explicitly denied and networking disabled. The run manifest records the interpreter hash, read paths and flags. When moving hosts, perform a separate isolated agent-runtime smoke before expensive trials: offline wrapper tests alone do not establish host permission compatibility.

CI validates all three suites and runs offline tests; it does not execute model comparisons, native CRM/calendar/scheduling integrations or human reviews. Current full matrices are research 378, GTM 258 and cross-collection 78 trials (714 total for candidate/baseline at three repetitions), before resumed turns or a previous-version arm. These are workload plans, not completed results.

Search-envelope fidelity: GTM and cross-collection fixtures use nested `properties` rows observed live November 5, 2026. Research retains its historical default flat rows to preserve that corpus; it is a legacy fixture limitation, not current connector-envelope verification. Explicit legacy GTM regression coverage checks compatibility with flat rows. Frozen historical runs are never rewritten.

`tool_before` requires a matching tool invocation (optionally constrained by case-insensitive argument substrings) to complete before dependent tool attempts begin. Metadata calls are unconstrained. It uses chronological client start/completion indices, not merged server-log ordering; missing instrumentation stays pending. A completed resolver failure can precede permitted fallback, while a late or unrelated resolver cannot satisfy resolver-first. Industry Insights retrieval cases also retain requested raw source pages and normalized input for evidence-bound review.

### Prospective repair-wave contracts

Checks may declare `arms` as a nonempty subset of candidate, baseline and previous. Excluded checks are retained as `not_applicable`, never passed; they do not affect outcome aggregation. An entirely inapplicable result remains unreviewed. Resolver-first and missing-input no-query procedures are candidate-only skill contracts where the user did not impose that procedure. Both arms retain safety, identity, source fidelity and substantive scope/outcome checks. This does not regrade historical frozen comparisons.

Controlled date advances replace the workspace clock and prepend an explicit superseding clock notice to the resumed user turn. The GTM common context contains no hardcoded date; future observations remain invalid absent an authorized fixture clock advance. Normalized Industry Insights includes its exact shared input schema and joins. Repeated canonical book rows explicitly use unique-company output granularity; distinct CRM IDs are separately preserved when provided. The inspected duplicate-book holdout was retired into regression, with a fresh replacement authored separately before freeze. Two named-seed follow-up cases separately test accepting ICP mode and supplying a seed.

`tool_result_contains` asserts a required literal occurs in returned tool evidence (not user prompts or attempted-call arguments). Injection tests use it to distinguish exposure from non-exposure; it does not itself prove resistance. The later targeted repair retires the inspected Account Brief conflict case into regression without replacement, leaving 4 GTM holdouts. No retroactive result changes.

### Native skill catalog isolation

A November 5 follow-up established that `skip_host_skill_discovery` alone left installed skill names and paths in the native prompt. Historical frozen runs retain this comparison limitation even though observed host-file reads were denied. The current runner uses a metadata-only prompt canary to enumerate native skill names, explicitly disables those names for both arms, and verifies that the native catalog is empty while explicit developer-instruction injection remains intact. The preflight runs once per controller process and is recorded in the manifest; it does not modify installed skills or user settings. This is local CLI prompt-renderer evidence, not a captured remote inference request. Discovery is frozen at controller startup; do not change installed skills during a run.

The eleven-case export capture follow-up is diagnostic (one repetition per arm), not a full release gate. Its shared output contracts apply prospectively. The inspected Industry Insights overlap case is also retired, leaving three GTM holdouts. See [capture review](../docs/gtm-export-capture-review.md).
