# GTM implementation status

## Current branch status

The `codex/gtm-skills-1.1.0` branch adds all five GTM skills on top of production identity-fix PR #8 (1.0.4). Collection and plugin versions are 1.1.0. Approved skill names are Account Brief, Account Signals, Prospect Finder, Account Prioritizer and Industry Insights. The production PR must merge before this branch is integrated.

Reviewer-feedback fixes, metadata corrections and the shared identity/presentation rules are included. See [reviewer feedback](gtm-reviewer-feedback-retest.md) and [identity-rule checks](identity-conflict-standardization.md). Historical results below describe earlier snapshots; they do not certify this branch for release. Earlier archives predate the final edits and must not be used as release artifacts.

## Historical implementation results

Completed implementation and requested testing/reporting on November 5, 2026, on `codex/gtm-skills-upgrade`, from baseline `fe4bcf7c20253661d440d88a8bc75d83832ae443`.

| Area | Status |
| --- | --- |
| Five GTM skill upgrades | Implemented, including targeted identity repair |
| Existing research skill source | All five trees unchanged |
| Offline checks | 229 passed |
| Corrected full GTM comparison | 258 completed; zero deterministic/infra failures; human review pending |
| Final targeted retests | 9 completed; zero deterministic/infra failures; human review pending |
| Research comparison | User-directed stop at 105/567 completion records; partial candidate/previous results have no deterministic failures |
| Further broad comparisons | Deferred at user's request; no runs active |
| Packages | Final 1.1.0 candidate built reproducibly; 20 archives, checksums, 14 CLI and 2 library-load smokes |
| Release approval/publication | Not approved or published |

The last Account Brief and fixture repairs have targeted evidence, not a newly completed full comparison. The inspected identity-conflict holdout is now regression; four public GTM holdouts remain. The independent ten-case challenge was not run. No failed or incomplete historical run was relabeled as passed.

See the [full validation report](gtm-validation-report.md) for results, limitations, source links and next steps; [draft release notes](gtm-release-notes.md) and [workflow guide](guides/gtm-workflows.md) are ready for review. Raw evidence and packages are local ignored artifacts and must be preserved separately from Git.

## Follow-up: targeted review, isolation and captures

Completed the requested steps 1–2. Nine prior targeted trials received source-bound machine review; human approval remains pending. Native catalog exposure was reproduced with the local CLI prompt renderer and fixed prospectively, preserving all ten explicit candidate skills. 76 affected offline tests pass. The bounded follow-up completed 22 trials (11 cases, two arms, one repetition), with zero deterministic/infrastructure failures and all 72 final-delivery files captured/hashverified. The new baseline audit observed no host-skill path attempts. Candidate skill hashes and packaged artifacts are unchanged.

See the [updated validation report](gtm-validation-report.md) for evidence and limitations. The next concrete candidate fix is consistent growth-field retrieval before scoring (earlier 83/81/83 variance); targeted retesting should remain limited to that repair. Human semantic signoff and the deferred full release gate remain outstanding. No broad run or release was performed.

## Growth scoring follow-up completed

Standardized both scoring skills’ growth retrieval with explicit unavailable-field fallback and zero-weight/no-requery boundaries. The affected canonical prospect now scores 81/81/81 across three targeted repetitions, with source/normalized/CSV/JSON parity. 20 scoring tests and both skill validators pass. See [growth review](gtm-growth-standardization.md); updated reproducible packages are in `dist/1.1.0-gtm-growth-standardized/`. The earlier next-fix item is resolved for the observed scenario; release and human semantic approval remain pending.
