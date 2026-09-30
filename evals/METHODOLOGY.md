# Evaluation methodology

Designed on 2026-09-30. This document describes implemented controls and the remaining limits; it is not a claim that the skills have passed a full release evaluation.

## Research basis

OpenAI's skill evaluation guidance treats skills as testable behavior: turn intended outcomes into rubrics, collect traces, and compare revisions using consistent cases. This framework keeps case definitions, traces, and outcome grading separate. [Testing Agent Skills Systematically with Evals](https://developers.openai.com/blog/eval-skills).

Anthropic distinguishes tasks, trials, transcripts, and actual outcomes; recommends combining code, model, and human graders; and separates improvement-oriented capability tests from regression protection. Here, saved-list success is determined from persisted fixture state, not the assistant's claim. [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents).

Recent skill-creator guidance emphasizes testing with and without a skill, isolated contexts, independent comparisons, triggering, and resource use. This implementation uses paired no-skill baselines and shuffled review packets. [Improving skill-creator: test, measure, and refine agent skills](https://claude.com/blog/improving-skill-creator-test-measure-and-refine-agent-skills).

The September 28, 2026 guidance on automated evaluation design emphasizes representative work, expert-agreed examples, calibration of graders, and held-out evidence rather than chasing an unreliable score. Our review checks are binary and evidence-bound; optional judge advice remains provisional until human review. [Automating eval design and hillclimbing](https://claude.dev/blog/automating-eval-design-and-hillclimbing/).

Infrastructure can change agent scores. We pin settings, record timeouts and errors, randomize job order, and preserve failures. Answer-key access is also a confound: the agent workspace contains only runtime skill content; fixtures, rubrics, and controller logs remain outside its permitted workspace. [Infrastructure noise](https://www.anthropic.com/engineering/infrastructure-noise), [Eval awareness and answer access](https://www.anthropic.com/engineering/eval-awareness-browsecomp).

## Experimental unit and comparison

A case is a natural user task with one or more turns and one fixture scenario. A trial is one independent execution of a case, with its own runtime workspace and fixture state. Follow-ups resume the same trial conversation; other trials start fresh. Scripted user replies exercise a fixed branch and are not a general user simulator.

The candidate and baseline receive the same user turns, clock, tool descriptions, fixture data, model, reasoning effort, execution limits, and host configuration. The candidate receives all available skill descriptions and can choose which files to read; no intended skill is named in its prompt. The no-skill baseline receives no skill catalog or skill files. The candidate's additional instruction tokens are part of the treatment and counted in usage. A previous skill tree may be evaluated as an additional arm.

The plan freezes all case/arm/repetition combinations before execution and shuffles them with a recorded seed. Repeated model sampling is not reproducible bit-for-bit; the seed controls scheduling, not the provider's randomness. Fixed concurrency reduces resource confounding but does not eliminate load variation. Never rerun a failure and keep only the successful attempt. Infrastructure retries, if needed, belong in a new linked run with the original preserved.

## Three layers of evidence

1. **Offline invariants:** fixture schema/query behavior, state changes, calculator outputs, grader failure handling, and statistical/reporting safeguards. CI executes these without model calls or service credentials.
2. **Replay behavior:** a real agent makes tool calls against a strict synthetic MCP subset. Tests cover ordinary tasks, boundaries, adversarial inputs, and multi-turn clarification. These measure behavior under controlled conditions.
3. **Live integration:** a separate, read-only check against the real connector, with approved examples and recorded entitlements/tool version. This is required before a production-readiness claim, but is deliberately excluded from replay comparisons because live data changes.

## Checks and review

Programmatic checks enforce causal invariants: no attempted write before authorization, required data retrieval where necessary, user-specified hard budgets, actual list membership, and explicit forbidden behavior. They do not prescribe one exact valid call sequence. Text matching is reserved for unambiguous strings; business judgment, completeness claims, questions, source grounding, and presentation use binary semantic rubrics.

Tool errors remain visible as diagnostic counts, including deliberate error injections. A successfully recovered validation error is not automatically a failed task: the skills explicitly permit a targeted metadata refresh and retry. Failure handling, bounded recovery, and eventual outcome are graded where the individual case requires them. During harness calibration we removed an initial blanket zero-error gate because it would penalize permitted recovery; earlier frozen runs retain their original checks.

Human labels identify the reviewer and cite evidence. Labels are bound to the exact transcript/state digest, so they cannot silently approve a changed run. Review packets hide treatment labels and randomize order. Reviewers should label a calibration set independently, discuss disagreements, and refine unclear rubrics before freezing the release set. The framework records individual labels but does not replace this adjudication process.

A model judge must differ from the candidate model. It receives rubric and observation packets without treatment identity; embedded instructions are untrusted evidence. Its proposed labels are stored separately and cannot satisfy the release gate. Calibration reports false passes explicitly. Human disagreement, case correlation, and limited sample size prevent a high raw agreement percentage from proving judge validity.

## Splits and leakage

Development cases support iteration; regression cases protect established behavior; holdout cases reserve distinct scenario families for a final check. Split validation rejects a family appearing in multiple splits. A paraphrase of a development task is not an independent holdout family. If a held-out failure informs a skill edit, retire that case into regression and commission a new held-out family before claiming fresh held-out performance.

Because this is a public repository, its holdout data is not cryptographically secret or immune to training contamination. Independent private cases are needed for consequential external claims. The runner's filesystem restrictions prevent ordinary runtime reads of controller files; they do not claim to defend against a compromised host or sandbox escape. Runtime self-reports that no files were read are not accepted as evidence.

## Reporting and decision policy

Every planned trial remains in the denominator. Missing or malformed artifacts become infrastructure errors. Pending semantics stay pending; a subset of deterministic passes cannot become an overall pass. A successful process exit is only execution status. The comparison uses common outcome checks across arms, excluding candidate-specific activation requirements.

For fully adjudicated matched runs, compute each case's mean candidate-minus-baseline success across paired repetitions. Estimate uncertainty by resampling whole scenario families and retaining paired repetitions and all cases within each sampled family. With fewer than five families or zero observed bootstrap variance, report only a descriptive delta. These are percentile bootstrap intervals, not guarantees; authored families are not proven independent samples from production, and a small synthetic corpus can still give misleadingly narrow intervals.

Report trial success and the observed fraction of cases whose every repetition passed. Do not call this an estimated pass^k probability, and do not use best-of-k success to hide inconsistency. Report tokens and latency alongside quality, without inventing monetary costs or normalizing away the skill's instruction overhead.

The initial release gate is intentionally strict: the full frozen suite, at least three trials per case, held-out coverage, every candidate check passing, and fully reviewed paired baseline evidence. It does not require positive measured lift when the baseline already solves a task. Separately inspect whether the skill adds enough value to justify its cost. A passing gate still requires human sign-off on live integration and representative coverage before a public readiness claim.

## Why the previous evaluator was not copied

The earlier internal evaluator contained useful task families and replay mechanics, but it used global plugin changes, partial filter emulation, response shapes that did not match current tools, permissive operator metadata, stale default assumptions, and graders that could penalize honest limitation disclosure. Reusing those scores would misstate current behavior.

The replacement uses immutable local runtime copies, current response envelopes, explicit unsupported-query errors, actual pagination and list state, current clarification requirements, a true no-skill arm, and review-dependent outcome grading. Former smoke walkthroughs are retained as diagnostics outside the published corpus; fictional companies in the new fixtures prevent synthetic facts from appearing to describe real businesses.
