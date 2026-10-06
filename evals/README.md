# Crunchbase skill evaluations

This is a repository-wide evaluation framework. The first suite covers the five skills in the private-company research collection; new Crunchbase workflows can add their own suite. The evaluator is development infrastructure, not an instruction file that users must install with a skill.

The framework runs a real agent against a local, stateful MCP fixture. It compares the current skills with the same agent and tools **without skills**, records actual tool effects, and leaves judgment-dependent checks pending until reviewed. It never connects to production Crunchbase or changes production saved lists.

## Requirements

- Python 3.11 or newer; the harness and offline tests use the standard library.
- An authenticated Codex CLI for behavioral runs. The initial implementation was exercised with `0.154.0-alpha.6.2`; permission-profile support is required. Recheck compatibility when upgrading.
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
