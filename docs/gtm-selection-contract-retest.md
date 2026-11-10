# Missing-factor selection contract retest

Only `priority-null-factor` was retested, once per candidate/baseline arm, in `evals/artifacts/gtm-selection-contract-repair/run-20261105T224526Z-dc488d28`.

The skill already excludes unscored accounts from actionable selection. Only this case's shared task instructions and artifact contract changed: `list_uuids` contains exactly scored output rows in rank order, excluding closed/insufficient-evidence rows while preserving the complete book in JSON/CSV. A critical arm-neutral exact-membership check was added. No skill, scoring code, fixture, or other case changed in this repair.

Both trials completed with zero deterministic/infrastructure failures. Both selected Mossrelay and Brambleflux only, retained all three accounts, and left Lumenquill score/tier/rank null with missing heat. JSON/CSV values agree and all six final files were captured/hash-verified. Six targeted capture-coverage tests and case validation passed. A read-only sensitivity check confirms the new oracle rejects the old baseline's extra unscored UUID while accepting the old candidate output; historical reports and labels were not rewritten.

The user explicitly passed original export-review item9 with its disclosed ambiguity. That approval is recorded separately in `evals/artifacts/gtm-export-capture-review/human-labels-step9.json`. These two new trials have machine verification only; their human semantic judgments remain pending. This one-repeat diagnostic is not a full release gate or evidence of closed-account behavior (this fixture tests missing heat).

Evidence: run `targeted-verification.json`, `membership-oracle-sensitivity.json`, `report.md`, and `evals/artifacts/gtm-selection-contract-repair-review/`.
