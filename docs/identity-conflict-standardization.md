# Identity-conflict standardization — two-part delivery

November 5, 2026.

## Production skills

Draft PR: https://github.com/crunchbase/crunchbase-mcp-skills/pull/8

Branch: `codex/reconcile-conflicting-company-identities`, based on current remote main `97eb2ce4fb8848253d034b26cd58d2527f3b6326`; change commit `7480b3f7b34cbfb18e8afb4f14ae32a49af9b7c1`. Created in an isolated checkout at `/private/tmp/crunchbase-identity-pr`; the existing GTM workspace was not staged, reset or switched. GitHub confirms exactly six changed paths: four production identity guides, Funding Signals Screener’s inline instructions, and a separate five-case identity-conflict regression selection. No GTM, release version, marketing names or artifacts are in this PR.

The rule pauses entity-dependent analysis or writes when returned evidence contradicts a supplied name/domain pair. Resolver confidence is not an override. Verified aliases/rebrands/legal names and explicit corrections remain supported. Independent confirmed entities may proceed unless unresolved membership could change aggregate denominators.

Validation: all five skill validators pass, suite validates with the production runner, and diff whitespace checks pass. Five candidate-only synthetic trials completed on gpt-6-astra / low using the current local isolation harness. Run: `evals/artifacts/production-identity-conflict/run-20261105T232838Z-a9d3f22a`. Zero deterministic failures or infrastructure errors. Assistant review: all five identify the conflict and request clarification; the capital case withholds its aggregate, and no saved-list writes occur.

Semantic judgments remain formally pending independent review. Brief and landscape outputs include internal instruction links; three provider validation errors are retained. These presentation/recovery observations are disclosed in the draft PR, not hidden behind a full-pass claim. Alias/correction exceptions were statically inspected, not separately replayed.

## Untracked GTM skills

All five GTM `references/entity-resolution.md` files now match the production PR’s generalized guide byte-for-byte. Account Brief’s earlier briefing-specific rule was generalized without dropping the conflict boundary. Each skill passes structural validation. The GTM packages remain untracked.

A separate `evals/suites/gtm/identity-conflicts.json` covers meeting briefs, monitoring, territory assignment, ranking and look-alike seed discovery. Focused run: `evals/artifacts/gtm-identity-conflict/run-20261105T233105Z-1879d4c0`. All five completed with zero deterministic failures and zero infrastructure errors. Assistant review confirms each asks the user to choose the intended entity before its dependent workflow. Tool logs contain only identity resolver, card-free identity-profile and metadata calls; no discovery, monitoring, scoring or saved-list writes occurred. All five responses also expose internal instruction links, and two provider validation errors were recorded. These remain presentation/recovery caveats rather than hidden full-pass claims; formal semantic checks are still pending independent review.

These are targeted one-repetition checks, not a full-suite/baseline comparison or release certification. No PR was merged, no package released, and names remain pending marketing approval.

## Internal-link presentation patch

PR #8 received a follow-up patch that explains identity questions through returned company facts. The instructions distinguish missing identity input from permission for a new action and prohibit internal rule citations in the response. The regression selection now checks for internal file paths and includes a semantic presentation criterion.

Only the two production cases with observed internal links were replayed: `brief-conflicting-identity` and `landscape-conflicting-identity`. Both now explain the conflicting facts and ask for the intended company, without instruction quotes or local links. The landscape response retains the accepted scope. Run: `evals/artifacts/production-identity-presentation/run-20261105T233553Z-88943651`. Both completed with zero deterministic failures and no infrastructure errors; semantic acceptance remains assistant review, not independent human signoff. Original failing outputs remain preserved.

The same wording and regression criteria were copied into the untracked GTM work to preserve consistency. GTM behavioral cases were not rerun for this presentation-only follow-up. The existing concise PR description was preserved.
