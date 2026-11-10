# Version 1.1.0 — draft release notes

**Unpublished candidate.** Use the [validation report](gtm-validation-report.md) for current failures, review requirements and release status. This document is not approval to publish.

This candidate adds five sales workflows: Account Brief, Account Signals, Prospect Finder, Account Prioritizer and Industry Insights. The existing five research skills remain available with unchanged source instructions. All ten skills are independently packaged with their references, helpers and license notices.

The GTM workflows use canonical company identity, explicit Crunchbase selection, accepted scope, sourced evidence and deterministic calculations. Unknown inputs remain unknown rather than becoming zero scores. CRM exports preserve record identity and currency; monitoring state advances only after successful complete output. Market direction requires complete denominators and sufficiently sized comparable segments. Scores and direction labels are heuristics, not purchase probabilities.

The evaluator now retains generated files and monitoring state, binds review judgments to their content, and covers GTM workflows and cross-skill routing alongside the existing research corpus. It preserves the existing independent human release-review requirement.

## Migrating from the downloaded pilot skills

- Use the new names prefixed with `crunchbase-` and preserve each complete skill folder.
- Normalize inputs to the documented versioned JSON schemas. Legacy scoring/query-plan arguments are not compatible with the new scoring and Industry Insights helpers.
- Establish a deliberate new baseline when monitoring state or scope is incompatible. Account Signals windows include exactly N calendar days ending on the as-of date; old window-policy state must not be silently reused.
- Use Python 3.10+ for GTM helpers. CSV/JSON workflows use the standard library; XLSX/XLSM CRM ingestion additionally needs openpyxl or a CSV conversion.
- Treat exports as files for review/import, not completed CRM updates. Calendars, native CRM reads, scheduling and durable storage depend on host capability. No skill authorizes outreach implicitly.

## Release assets and approval

After the validation report's release blockers and human review gates are resolved, publish the twenty individually verified `.zip`/`.skill` assets with their matching `SHA256SUMS`. Rebuild and rerun the required frozen comparison after any candidate implementation change. The current published download links remain at 1.0.3 until an approved release is actually published.
