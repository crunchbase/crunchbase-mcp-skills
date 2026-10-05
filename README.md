# Crunchbase MCP Skills

Reusable agent skills for working with Crunchbase through its Model Context Protocol (MCP) tools. This is Crunchbase's general skills repository: each skill packages a focused workflow, supporting instructions, and any calculation helpers it needs.

The initial collection covers private-company research, funding analysis, and saved lists. The repository can accommodate additional Crunchbase workflows without changing the scope of existing skills.

## Available skills

| Skill | Use it for | Result |
| --- | --- | --- |
| [Build thesis landscape](skills/crunchbase-build-thesis-landscape/SKILL.md) | Discover companies against a thesis | Segmented candidates, inclusion reasons, query scope, and an optional saved list |
| [Review funding signals](skills/crunchbase-review-funding-signals/SKILL.md) | Screen recently announced rounds | A review queue tied to your criteria, with dated rounds and linked companies |
| [Prepare company brief](skills/crunchbase-prepare-company-brief/SKILL.md) | Prepare for a company meeting | A concise brief covering business, financing, team, peers, and questions to test |
| [Analyze capital intensity](skills/crunchbase-analyze-capital-intensity/SKILL.md) | Compare funding within a confirmed company set | Period comparisons, concentration, formation, and explicit denominators |
| [Manage saved lists](skills/crunchbase-manage-saved-lists/SKILL.md) | Inspect, monitor, or change a list | Current membership or dated events; verified membership after requested changes |

See the [private-company research guide](docs/guides/private-company-research.md) for example requests, workflow boundaries, bounded resolver recovery, and calculation verification. Each calculation-enabled skill includes its own runtime and input instructions.

## Requirements

Use an agent that can load `SKILL.md` and its supporting files, with an authenticated Crunchbase connection exposing the [required tools](MCP-REQUIREMENTS.md). Skills do not install a connector or grant Crunchbase data access. Account entitlements determine available fields and operations. Python 3 is needed for skills that use the bundled calculation helper.

These workflows were developed for Codex. Other skill-compatible agents need equivalent tools and local file access; compatibility must be verified for each host.

## Install

From a local checkout, with Node.js and npm available:

```sh
# List skills without installing.
npx skills add . --list

# Choose skills and a target agent.
npx skills add .

# Install a single skill.
npx skills add . --skill crunchbase-prepare-company-brief
```

The repository supports multiple skills. Each directory under `skills/` is independently installable; retain its references, scripts, assets, and agent metadata. Avoid installing renamed copies of the same workflow together, since competing definitions can make routing ambiguous.

The root `.codex-plugin/plugin.json` packages this collection as the **Crunchbase MCP Skills** Codex plugin. The individual skill directories are also usable without that wrapper.

After a revision has been published to [crunchbase/crunchbase-mcp-skills](https://github.com/crunchbase/crunchbase-mcp-skills), it can be installed with:

```sh
npx skills add crunchbase/crunchbase-mcp-skills --list
npx skills add crunchbase/crunchbase-mcp-skills --skill crunchbase-prepare-company-brief
```

These remote commands use the published repository, not unpushed local changes. Use the checkout commands above to test a local candidate. The [skills CLI](https://github.com/vercel-labs/skills) supports multi-skill repositories; [skills.sh discovery](https://www.skills.sh/docs/faq) follows CLI installation telemetry.

## Development

Keep each skill focused on a distinct user task and declare its own required inputs, tool access, and output expectations. New workflows do not need to be about venture capital or private-company sourcing. See [contributing](CONTRIBUTING.md) for repository conventions and validation expectations.

The [evaluation framework](evals/README.md) provides controlled MCP fixtures, repeated comparisons with and without skills, multi-turn checks, outcome grading, and blinded review. Its first suite covers the current private-company research collection; additional collections can bring their own cases and fixtures. Evaluation infrastructure lives outside the installable skills.


## License

Skill instructions and code are provided under the [MIT License](LICENSE). Crunchbase data access and use remain subject to the applicable service terms; this license does not grant service access or trademark rights. Bundled Crunchbase brand assets retain their existing terms and are excluded from the code license. See [NOTICE](NOTICE).
