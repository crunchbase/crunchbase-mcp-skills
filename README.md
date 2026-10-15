# Crunchbase MCP Skills

Agent skills for company research, funding analysis, and saved lists, powered by Crunchbase MCP.

Build an investment landscape, screen recent funding rounds, prepare for a company meeting, or compare capital across a market. Each skill packages a focused workflow with supporting references and calculation helpers where needed.

## Get started

You need a Crunchbase account with MCP access. Follow the [Crunchbase connection guide](https://data.crunchbase.com/docs/connecting-ai-tools) to connect your agent and sign in. For Claude.ai, start with the [Crunchbase connector](https://claude.com/marketplace/connectors/crunchbase-mcp).

Install with the [skills CLI](https://github.com/vercel-labs/skills), then choose the skills and agent you want:

```sh
npx skills add crunchbase/crunchbase-mcp-skills
```

Requires Node.js and npm. The installer defaults to the current project; add `--global` for personal use across projects. For Claude.ai, use the [ZIP upload instructions](#claudeai).

After installation, try:

> Use Crunchbase to prepare a brief on Canva for an introductory meeting. Include financing, relevant peers, and questions to explore.

Skills require the [Crunchbase MCP tools](MCP-REQUIREMENTS.md); installing them does not provide a connection or account access. Calculation helpers require Python 3.9+ and use only the standard library.

## Choose a skill

| Skill | What it does | Example request |
| --- | --- | --- |
| [Build thesis landscape](skills/crunchbase-build-thesis-landscape/SKILL.md) | Discover and segment companies against an investment thesis; optionally save the reviewed set. | “Use Crunchbase to map US seed-stage companies building security tools for developers.” |
| [Review funding signals](skills/crunchbase-review-funding-signals/SKILL.md) | Screen recent funding rounds against your mandate. | “Use Crunchbase to find European fintech companies that announced Series A rounds in the past 90 days.” |
| [Prepare company brief](skills/crunchbase-prepare-company-brief/SKILL.md) | Prepare a meeting brief covering the business, financing, team, peers, and questions to explore. | “Prepare a Crunchbase brief on Canva for an introductory meeting.” |
| [Analyze capital intensity](skills/crunchbase-analyze-capital-intensity/SKILL.md) | Compare funding, concentration, and company formation within a confirmed universe. | “Use Crunchbase to compare funding concentration across the companies in my Infrastructure Watchlist.” |
| [Manage saved lists](skills/crunchbase-manage-saved-lists/SKILL.md) | Inspect a list, review activity, or make explicitly requested membership changes. | “Show the current companies in my Infrastructure Watchlist on Crunchbase.” |

The skills instruct the agent to ask for missing inputs and resolve ambiguous company identities before continuing. Research stays read-only unless you explicitly request a supported saved-list change. Write workflows require a preview and membership verification; the preview does not require another approval when the requested action is already clear.

See the [workflow guide](docs/guides/private-company-research.md) for more examples and expected outputs.

## Installation options

Each folder under `skills/` is independently installable. Keep the complete folder, including supporting files and license notices. Choose one installation method per workflow to avoid duplicate definitions.

<details>
<summary><strong>Claude Code and Codex: install options</strong></summary>

To install only the company-brief skill for a specific agent:

```sh
# Claude Code
npx skills add crunchbase/crunchbase-mcp-skills --skill crunchbase-prepare-company-brief --agent claude-code

# Codex
npx skills add crunchbase/crunchbase-mcp-skills --skill crunchbase-prepare-company-brief --agent codex
```

These commands use the published default branch, not a pinned release. Add `--global` for a personal installation across projects, or `--list` to inspect available skills without installing.

From an existing local checkout, install that checkout's contents with:

```sh
npx skills add .
```

For manual Claude Code installation, copy the selected folder to `~/.claude/skills/` for personal use or `.claude/skills/` in your target project. See the [Claude installation guide](docs/guides/claude-installation.md).

The repository also includes optional [Codex plugin packaging](.codex-plugin/plugin.json) for the whole collection. Individual skills can be installed without it.

</details>

### Claude.ai

<details>
<summary><strong>Prepare and upload a skill ZIP</strong></summary>

Enable code execution in Claude and upload one skill as a ZIP through its skill settings. The archive must contain the named skill folder, with `SKILL.md` inside that folder. See [Anthropic's upload instructions](https://support.claude.com/en/articles/12512198-how-to-create-custom-skills).

Download and extract the [repository source](https://github.com/crunchbase/crunchbase-mcp-skills/archive/refs/heads/main.zip), or clone it with Git. On macOS or Linux, run these commands from the repository root to create a company-brief ZIP:

```sh
cd skills
zip -r ../crunchbase-prepare-company-brief.zip crunchbase-prepare-company-brief \
  -x '*/__pycache__/*' '*.pyc' '*/.DS_Store'
```

Upload `crunchbase-prepare-company-brief.zip` from the repository root. Use the corresponding folder name to package another skill; preserve its bundled scripts when present.

</details>

### Downloads

Build an individual `.skill` and `.zip` archive for every skill from a local checkout:

```sh
python3 scripts/build_releases.py
```

The output directory must be empty; use `--output <fresh-directory>` for another build. Files are written to `dist/<version>/` with a `SHA256SUMS` checksum file. Each archive includes the complete skill folder and its version. The `.skill` files contain the same ZIP data; use `.zip` for Claude.ai uploads.

Download individual skills from [v1.0.1](https://github.com/crunchbase/crunchbase-mcp-skills/releases/tag/v1.0.1). Use ZIP for Claude.ai uploads.

| Skill | ZIP | .skill |
| --- | --- | --- |
| Thesis landscape | [Download](https://github.com/crunchbase/crunchbase-mcp-skills/releases/download/v1.0.1/crunchbase-build-thesis-landscape.zip) | [Download](https://github.com/crunchbase/crunchbase-mcp-skills/releases/download/v1.0.1/crunchbase-build-thesis-landscape.skill) |
| Funding signals | [Download](https://github.com/crunchbase/crunchbase-mcp-skills/releases/download/v1.0.1/crunchbase-review-funding-signals.zip) | [Download](https://github.com/crunchbase/crunchbase-mcp-skills/releases/download/v1.0.1/crunchbase-review-funding-signals.skill) |
| Company brief | [Download](https://github.com/crunchbase/crunchbase-mcp-skills/releases/download/v1.0.1/crunchbase-prepare-company-brief.zip) | [Download](https://github.com/crunchbase/crunchbase-mcp-skills/releases/download/v1.0.1/crunchbase-prepare-company-brief.skill) |
| Capital intensity | [Download](https://github.com/crunchbase/crunchbase-mcp-skills/releases/download/v1.0.1/crunchbase-analyze-capital-intensity.zip) | [Download](https://github.com/crunchbase/crunchbase-mcp-skills/releases/download/v1.0.1/crunchbase-analyze-capital-intensity.skill) |
| Saved lists | [Download](https://github.com/crunchbase/crunchbase-mcp-skills/releases/download/v1.0.1/crunchbase-manage-saved-lists.zip) | [Download](https://github.com/crunchbase/crunchbase-mcp-skills/releases/download/v1.0.1/crunchbase-manage-saved-lists.skill) |

[SHA-256 checksums](https://github.com/crunchbase/crunchbase-mcp-skills/releases/download/v1.0.1/SHA256SUMS). The build command above packages the files in your checkout.

## Agent requirements

Use an agent that can load `SKILL.md`, read bundled files, and call the [required Crunchbase MCP tools](MCP-REQUIREMENTS.md). The instructions use paths relative to each skill folder and resolve tool names through the host's connection. Host-specific metadata is optional.

See the [Claude installation guide](docs/guides/claude-installation.md) for Claude Code and Claude.ai setup.

## How it works

The agent selects a skill from its description, reads `SKILL.md`, and loads supporting references as needed. Mention Crunchbase in your request and include the company, mandate, or saved list you want to work with.

The workflows resolve company identities, retrieve the relevant records, and produce linked results with explicit dates, filters, and coverage. Missing data stays unknown, and interpretation is separated from returned facts.

```text
skills/<skill-name>/
├── SKILL.md       # Workflow and activation instructions
├── references/   # Supporting guidance
├── scripts/      # Calculation helpers, where needed
├── assets/       # Bundled assets
├── agents/       # Optional host metadata
├── LICENSE
└── NOTICE
```

## Contributing

New Crunchbase workflows and improvements to existing skills are welcome. See [contribution guidelines](CONTRIBUTING.md) and [tool requirements](MCP-REQUIREMENTS.md).

The collection and its skills share the version in [VERSION](VERSION). Release tags use `v<version>`. See [release versioning](CONTRIBUTING.md#version-a-release) for maintainer instructions.

For issues, include the skill, release version, agent, request, and expected result. Remove credentials and private data from examples.

## License

Skill instructions and code are provided under the [MIT License](LICENSE). Crunchbase data access and use remain subject to the applicable service terms; this license does not grant service access or trademark rights. Bundled Crunchbase brand assets retain their existing terms and are excluded from the code license. See [NOTICE](NOTICE).
