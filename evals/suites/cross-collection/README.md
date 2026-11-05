# Cross-collection routing corpus

Thirteen cases exercise the expanded catalog: ten paired workflow boundaries (regression) and three unrelated requests (two development, one held-out). The candidate sees all ten skill descriptions. Each boundary checks the intended skill activates, its adjacent skill does not, and the actual requested outcome remains in scope. The baseline receives identical tools/data/context without skill files; activation is excluded from common baseline outcomes.

Boundaries cover seller-specific meeting prep versus a neutral tearsheet, account signals versus saved-list membership, sales market direction versus capital analysis, prospect discovery versus research mapping, and account tiering versus funding screening. Generic requests should neither activate Crunchbase skills nor call task tools.

This is routing/task-boundary coverage, not proof of the complete Radar → Prospect Finder → Prioritize → Pulse artifact handoff chain. That chain and live discovery in supported hosts require separate evidence. The fixture shares the GTM synthetic contract and limits documented in `../gtm/README.md`. Research behavior must also be rerun using the existing 63-case corpus with the expanded catalog and, when available, the pre-change skill tree as a `previous` arm.

```sh
python3.12 evals/run.py validate --suite evals/suites/cross-collection/suite.json --split all
python3.12 evals/run.py plan --suite evals/suites/cross-collection/suite.json --split all --repeats 3 --arms candidate,baseline
```

The full paired three-repeat matrix contains 78 trials. Use the same strict human-review release gate; a routing pass alone is not release approval. The public held-out case is an organizational boundary, not a secret or independently sealed benchmark.
