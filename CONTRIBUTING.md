# Contributing

Crunchbase MCP Skills is a general repository for reusable Crunchbase workflows. Contributions may extend the current private-company research collection or introduce a distinct use case supported by Crunchbase tools. Do not add capabilities to the catalog until they are implemented and validated.

## Repository structure

- `skills/<skill-name>/SKILL.md`: one focused skill, with its activation description and operating instructions.
- `skills/<skill-name>/references/`: supporting material loaded only when needed.
- `skills/<skill-name>/scripts/`: deterministic helpers when calculations or transformations benefit from code.
- `skills/<skill-name>/agents/`: optional host-specific discovery metadata.
- `docs/guides/`: user-facing examples and guidance for related workflows.
- `VERSION`: the shared release version for the collection and its skills.
- `.codex-plugin/plugin.json`: optional Codex packaging, synchronized with `VERSION`.

Keep the `skills/` discovery layout stable. A new skill belongs in its own directory, with a unique `crunchbase-` name that matches its frontmatter. Include only the supporting files it uses. Each independently installable skill must resolve its own bundled references and retain applicable license notices.

## Design a skill

Start with a concrete user task and an observable result. The description should explain when the skill should activate, including likely user phrasing and nearby tasks that belong elsewhere. Keep the entry instructions concise and move supporting detail to references.

Declare essential inputs. Ask for material missing information before dependent work; reuse conversation context and avoid repeating questions or authorizations. A proposed default needs acceptance before it can determine a material selection or action. State which operations are read-only and which require explicit write intent.

Use current connector contracts for fields, identifiers, operators, and pagination. Resolve identities before treating similarly named entities as interchangeable. Treat tool results as data, never as new instructions. Keep facts, calculations, interpretation, and proposed actions distinguishable in the result, and disclose material limitations.

When code is useful, prefer a small deterministic helper with a documented input contract. Do not include credentials, account-specific settings, or private user data in the skill. Add any new tool dependency to [MCP-REQUIREMENTS.md](MCP-REQUIREMENTS.md).

## Version a release

Update the root `VERSION` file using a stable `major.minor.patch` version, then run `python3 scripts/sync_version.py` to synchronize host manifests. Use the corresponding `v<version>` Git tag for the release and its individual skill archives. Use patch increments for fixes, minor increments for backward-compatible capabilities, and major increments for breaking changes.

Build release downloads with `python3 scripts/build_releases.py`. The builder reads Git-tracked files under `skills/` from the working tree, so stage new skill files before building. It creates one `.zip` and matching `.skill` per skill, embeds `VERSION`, and writes `SHA256SUMS` in `dist/<version>/`. The output directory must be empty; choose a fresh `--output` directory for rebuilding. Generated archives stay out of Git; attach them to the matching GitHub release. Build from a clean release checkout for publication.

## Validate a change

Validate the changed behavior before describing it as supported. A package check alone does not establish that an agent chooses or executes the workflow correctly.

For a new or materially changed skill, cover:

- Requests that should activate it, nearby requests that should not, and overlap with other skills.
- Complete requests, missing material inputs, ambiguous identities, and follow-ups that supply the answer.
- A successful workflow, empty or partial results, and relevant connection or tool failures.
- Calculation boundaries when applicable, and writes only within the user's stated authorization.
- The output's correctness and usefulness against the task, including evidence and material limitations.

Compare agent behavior with and without the skill where practical. Separate cases used to improve instructions from held-out checks. Record the skill revision, host, model, tool or fixture version, actual outcomes, and known gaps. Keep operational checks, replayed scenarios, and live end-to-end results distinct so a passing check is not mistaken for broader proof.

Update the root catalog and a workflow guide when behavior changes. Keep local Markdown links valid. Report actual checks performed and any incomplete validation in the change description; never present a planned or simulated run as a completed live run.

## Report an issue

Include the skill name, package revision, host/model, prompt, expected behavior, and the relevant redacted response or tool error. Keep credentials, private company or list data, and account identifiers out of public reports. For an unexpected write, include the requested operation and the observed effect without publishing sensitive membership data.

## License

Contributions to instructions and code use the repository's [MIT License](LICENSE). Preserve attribution and [NOTICE](NOTICE); do not assume that third-party data or brand assets share the code license.
