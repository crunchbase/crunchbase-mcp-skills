# GTM metadata consistency audit

November 5, 2026. Compared all five GTM skills with all five existing production skills in this checkout. Names and package metadata were not changed; marketing naming remains pending. This is a static consistency audit, not a behavioral retest or installed-host certification.

## Consistent

- All ten entrypoints use the same frontmatter fields: name, description and MIT license. Names match their directories.
- All ten have display names, short descriptions, self-referencing invocation prompts, the Crunchbase MCP dependency and implicit invocation enabled.
- Short descriptions are 41–50 characters across the collection.
- All ten bundle identical LICENSE and NOTICE content and the Crunchbase icon asset.
- Plugin registration uses the common ./skills/ directory; it does not require a separate per-skill registration entry.
- VERSION and plugin version are synchronized at 1.1.0.
- Existing five production skill trees have no diff against baseline fe4bcf7c20253661d440d88a8bc75d83832ae443.

## Findings

1. Industry Insights lacks icon_small, icon_large and brand_color in agents/openai.yaml. Every production skill and the other four GTM skills declares these. Its image asset is already bundled. Recommended: add the same two ./assets/crunchbase-icon-blue.png references and #146AFF color.
2. Account Brief and Account Signals use the generic default prompt “for my Crunchbase sales workflow.” Production skills and the other GTM skills use task-specific prompts. Recommended: describe meeting preparation and account monitoring respectively while retaining current identifiers until marketing approves names. Dependency descriptions for these two are also generic; task-specific wording would improve consistency but is not a functional dependency defect.
3. All five GTM folders are currently untracked by Git. The standard scripts/build_releases.py builder reads only git ls-files, so a build from the current index would omit these packages. This is a release-preparation blocker, not a metadata syntax error. Ensure intended GTM files are tracked before the final standard release build; do not include caches or evaluation artifacts. No staging or build was performed by this audit.

## Naming handoff

Once names are approved, reconcile directory name, SKILL.md name, agents/openai.yaml display_name and default_prompt, documentation, suite references and archive names together. Do not change stable identifiers based solely on a display-label decision without deciding whether identifiers should change. Rebuild archives after final edits.

## Remediation

Findings 1 and 2 are resolved: Industry Insights now declares both bundled icon references and the shared brand color; Account Brief and Account Signals now have task-specific default prompts and dependency descriptions. Skill identifiers, display names, dependency identifiers and invocation policies are unchanged. All ten metadata files parse, reference their own skill in the default prompt, and resolve their icon assets. Finding 3 remains for release preparation. No behavioral reruns were needed for these metadata-only edits.

## Second consistency pass

All ten skills pass the skill-creator structural validator. Interface keys, icon bytes and paths, brand color, self-invocation prompts, frontmatter names and package versions are consistent. Concrete Markdown links and entrypoint reference/script paths resolve; generic `references/...` and `scripts/...` examples in production instructions are illustrative, not missing dependencies. No symlinks were found in skill packages.

Shared-contract comparison:

- `query-core.md` is byte-identical across all ten skills.
- `saved-lists.md` is byte-identical across all five skills that bundle it.
- GTM output-contract changes intentionally replace investment context with sales context; Prospect Finder additionally includes its tested missing-seed clarification. These are appropriate workflow differences, not accidental metadata drift.
- Account Brief alone has the strengthened conflicting-name/domain rule added during earlier testing. The other eight copies of `entity-resolution.md` remain identical to the production version. Those copies require identity confirmation and ambiguity handling, but do not explicitly state that resolver confidence cannot override contradictory supplied identity anchors. This is a shared-policy consistency gap, not evidence of eight observed behavioral failures. Recommended follow-up: generalize the rule beyond briefing language, propagate it to applicable workflows, and run a narrowly scoped identity-conflict check rather than another full suite. Funding Signals Screener has no bundled copy; inspect its own identity path before deciding whether any change applies.

The existing Git-tracking/build blocker remains. Naming and final archive rebuilding remain deferred. This pass changed only this audit record; no skill behavior, names, staging state or archives were changed.

## Identity-policy follow-up

The shared identity gap has now been addressed in two parts: production-only draft PR [#8](https://github.com/crunchbase/crunchbase-mcp-skills/pull/8), then the matching rule in all five untracked GTM guides. The production working tree here remains unchanged; the PR was prepared in an isolated checkout. See [validation and delivery details](identity-conflict-standardization.md). Names, staging and release archives remain unchanged.
