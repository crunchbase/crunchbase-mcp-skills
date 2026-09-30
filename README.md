# Crunchbase MCP Skills

Five focused skills for private-company research using a connected Crunchbase data source. Build a company landscape, screen recent funding, prepare a meeting brief, analyze a confirmed company universe, or manage a saved list.

| Skill | Use it for | Result |
| --- | --- | --- |
| [Build thesis landscape](skills/crunchbase-build-thesis-landscape/SKILL.md) | Discover companies against a thesis | Segmented candidates, inclusion reasons, query scope, and an optional saved list |
| [Review funding signals](skills/crunchbase-review-funding-signals/SKILL.md) | Screen recently announced rounds | A review queue tied to your mandate, with dated rounds and linked companies |
| [Prepare company brief](skills/crunchbase-prepare-company-brief/SKILL.md) | Prepare for a company meeting | A concise brief covering business, financing, team, peers, and questions to test |
| [Analyze capital intensity](skills/crunchbase-analyze-capital-intensity/SKILL.md) | Compare funding within a confirmed company set | Period comparisons, concentration, formation, and explicit denominators |
| [Manage saved lists](skills/crunchbase-manage-saved-lists/SKILL.md) | Inspect, monitor, or change an existing list | Current membership or dated events; verified membership after requested changes |

## Before installing

You need an agent that can load `SKILL.md` and its supporting files, plus an authenticated Crunchbase connector exposing the [required tools](MCP-REQUIREMENTS.md). Python 3 is needed for the bundled calculation helper. The skills do not install a connector, provide credentials, or grant Crunchbase data access. Account entitlements determine which data and list operations are available.

The workflows were developed for Codex. Other skill-compatible agents also need the same tool capabilities and file access; cross-agent behavior has not been verified for this revision.

## Install from this checkout

With Node.js and npm available, run these commands from the repository root:

```sh
# Inspect the five available skills without installing.
npx skills add . --list

# Choose which skills and agent to install to.
npx skills add .

# Or install only the company-brief skill.
npx skills add . --skill crunchbase-prepare-company-brief
```

Alternatively, copy individual directories from `skills/` into your agent's skill location. Keep each directory intact, including its references, scripts, assets, and optional agent metadata. Install one copy of each workflow; installing this collection alongside another renamed edition can give the agent duplicate choices.

The root `.codex-plugin/plugin.json` supplies the Codex plugin wrapper. The `skills/` directories can also be distributed individually.

The repository is [crunchbase/crunchbase-mcp-skills](https://github.com/crunchbase/crunchbase-mcp-skills). Once the skills have been published there, install them with:

```sh
npx skills add crunchbase/crunchbase-mcp-skills --list
npx skills add crunchbase/crunchbase-mcp-skills --skill crunchbase-build-thesis-landscape
```

The [skills CLI](https://github.com/vercel-labs/skills) supports multiple skills in one repository. According to the [skills.sh FAQ](https://www.skills.sh/docs/faq), leaderboard discovery follows CLI installation telemetry. The commands above target the published repository; unpublished local changes are available only through the local-checkout installation instructions.

## Try a workflow

- **Landscape:** “Use Crunchbase to map software for independent dental practices. Segment companies by the workflow they serve.”
- **Funding:** “Use Crunchbase to screen European seed rounds in climate software announced in the past 30 days.”
- **Company brief:** “Use Crunchbase to prepare a meeting brief on Canva, including financing, team, peers, and questions to test.”
- **Capital analysis:** “Use Crunchbase to analyze capital intensity across this confirmed company set: Canva, Figma, and Miro. Compare the trailing 12 months with the preceding 12 months.”
- **Saved list:** “Use Crunchbase to inspect my ‘Climate software’ list and summarize its current membership.” Replace the example list name with your own.

To save a newly discovered landscape, include “save the reviewed companies to a new list named …” in the landscape request. To append companies to an existing list, name the list and the companies explicitly. The agent previews canonical identities before the write and checks persisted membership afterward.

## Scope and defaults

The skills activate for an explicit Crunchbase request, a selected Crunchbase source, or a continuation of an active workflow. A landscape needs a usable thesis; capital analysis needs a confirmed company set. The agent asks when an essential identity or input is ambiguous.

Your stated mandate controls the screen. When a missing input would materially change the companies selected, the analysis, or a saved-list action, the agent asks one focused question covering the unresolved essentials. It reuses answers already supplied and offers concrete options when helpful. Proposed defaults require acceptance; an unspecified geography or stage is not silently interpreted as unrestricted, and an omitted funding window is not silently interpreted as 30 days. An explicit request for a broad screen is sufficient to proceed broadly.

A first-pass landscape is bounded and labeled with what was retrieved and reviewed; an explicit complete request requires the relevant pagination. Confirmed-list results are never presented as whole-market estimates.

For example, “US, pre-seed through Series A, operating private companies with less than $15 million raised” is a valid mandate when you request it. It is not an automatic filter applied to every landscape.

Outputs distinguish retrieved facts, calculations, interpretation, and suggested actions. A dash means no value was returned for that field. Material limitations—such as partial retrieval, unresolved identities, or excluded amounts—are stated with their effect on the conclusion. No returned event is not evidence that no event occurred.

## Maintenance and feedback

When reporting an issue, include the skill name, package version, host/model, prompt, expected behavior, and the relevant redacted response or tool error. Keep credentials and private company/list data out of public reports. The existing evaluation suite is maintained separately and is not included or rerun as part of this revision.

## License

The skill instructions and code are provided under the [MIT License](LICENSE). The package retains the existing Crunchbase attribution. Crunchbase data access and use remain subject to the applicable service terms; this code license does not grant access to the service or trademark rights. Bundled Crunchbase brand assets are excluded from the code license and retain their existing terms.
