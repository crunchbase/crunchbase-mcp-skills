# Install in Claude

Install individual Crunchbase skills in Claude Code or upload them to Claude.ai. Each skill includes its own instructions and supporting resources. The collection version is recorded in [VERSION](../../VERSION).

Before installing, connect and authenticate Crunchbase using the [connection guide](https://data.crunchbase.com/docs/connecting-ai-tools). Your account needs MCP access and the [tools required by the workflow](../../MCP-REQUIREMENTS.md). Calculation helpers require Python 3.9 or later and use only the standard library.

## Claude Code

Copy the complete selected skill directory from `skills/` to either:

- `~/.claude/skills/<skill-name>/` for personal use.
- `.claude/skills/<skill-name>/` in a target project for project use.

For example, the resulting entry point for a personal company-brief installation is `~/.claude/skills/crunchbase-prepare-company-brief/SKILL.md`. Keep its supporting files alongside it. Invoke `/crunchbase-prepare-company-brief` or ask naturally for a Crunchbase company brief. These locations and invocation mechanisms are documented in [Claude Code's skills guide](https://code.claude.com/docs/en/skills).

The repository's `skills/` directory is a distribution layout; merely cloning it does not install personal or project Claude Code skills. `.codex-plugin/plugin.json` is optional Codex packaging, and `agents/openai.yaml` supplies optional OpenAI metadata. Neither is a Claude installer or MCP configuration. Claude use does not depend on those files.

## Claude.ai

Package one skill folder per ZIP, keeping the named folder at the archive root:

```text
crunchbase-prepare-company-brief.zip
└── crunchbase-prepare-company-brief/
    ├── SKILL.md
    ├── references/
    ├── assets/
    ├── agents/
    ├── LICENSE
    └── NOTICE
```

Calculation-enabled packages must also retain `scripts/`. Enable code execution and upload the ZIP through Claude's skill settings. Use the `.zip` format for uploads. See [creating custom skills](https://support.claude.com/en/articles/12512198-how-to-create-custom-skills) and [using skills](https://support.claude.com/en/articles/12512180-use-skills-in-claude).
