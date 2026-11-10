# Recurring comparisons

Set up a recurring task only when requested, using the host's actual capabilities and the user's existing authorization. Do not prescribe unverified product UI steps or require a second confirmation when the user already authorized creation. Never send messages independently from this skill.

An unattended run needs accepted scope, canonical account/list/seed identifiers, exclusions, as-of timezone, rubric, output destination, connector access, Python and durable state. Missing required inputs or capability: report one actionable failure; never guess. If the host cannot run the helper, provide the configured prompt as an artifact and accurately report that recurring execution is not established.

Use `--state` to compare and `--write-state` only after complete retrieval, scoring and artifact generation. State is versioned and atomically replaced. Changed scope/rubric/workflow requires a new baseline, not a performance-change claim. A first run establishes a baseline; without a prior snapshot, a dated event window does not prove a company newly matches the ICP. Never rebuild exact previous scores from prose or edit state by hand.

Account Prioritizer: report tier/eligibility changes, additions/removals, and evidence behind movements. Prospect Finder: report newly matching canonical UUIDs and changed eligibility under the same complete search scope; separately describe new events as dated evidence, not proof of a transition. Use persistent full-pool state, not only the displayed top N. On failure preserve the prior state and do not publish a partial ranked alert. On unchanged non-actionable runs follow the user's notification preference and stay quiet by default. A new error or action needed is reportable.
