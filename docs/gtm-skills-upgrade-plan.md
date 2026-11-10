# GTM skills assessment and upgrade plan

Draft dated November 5, 2026. Baseline: local repository commit `fe4bcf7c20253661d440d88a8bc75d83832ae443` (version 1.0.3). Incoming source: `/Users/victor.mach/Downloads/gtm skills`, containing five skill ZIPs and an evaluation suite.

See the [autonomous swarm execution and evaluation plan](gtm-swarm-execution-plan.md) for agent ownership, work waves, prior test evidence, harness extensions, and release gates.

Keep all five GTM workflows as a distinct collection alongside the existing private-company research skills. Preserve their sales-specific outcomes, deterministic helpers, CRM context, and useful handoffs. Bring their activation, clarification, retrieval, evidence, calculations, and evaluation contracts into line with the local repository before adding them to the production catalog. Do not merge away their sales use cases or import the ZIPs unchanged.

This assessment combines three parallel reviews: workflow and user experience; data contracts and calculations; evaluation and release packaging. It examines source and includes focused offline scoring checks. It does not establish live connector compatibility or release readiness. The pilot Word documents and presentation were not assessed.

## Preserve the five workflows

| Incoming skill | Proposed repository name | Core behavior to retain | Boundary against existing skills |
| --- | --- | --- | --- |
| Account Brief | `crunchbase-account-brief` | Seller-specific meeting preparation, first meeting versus follow-up, CRM history, sourced talking points and suggested wording | Tearsheet remains the general private-company brief. Account Brief owns sales preparation when seller context or sales intent is explicit. |
| Prospect Finder | `crunchbase-prospect-finder` | ICP and customer look-alike discovery, exclusions, ranked CSV, separate buyer-fit hypotheses | Market Map owns investment landscapes. Finder owns new sales targets, not ranking an existing account book. |
| Account Prioritizer | `crunchbase-account-prioritizer` | Reproducible tiers for an existing account book, adjustable rubric, CRM identifiers and export formats | Funding Screener owns recent-round mandate screening. Prioritize owns account-book scoring, not event alerts. |
| Account Signals | `crunchbase-account-signals` | Dated signals across existing accounts, ranked plays, prediction history, optional recurring change detection | Watchlists owns saved-list operations and general monitoring. Account Signals owns seller-specific account signals and plays. |
| Industry Insights | `crunchbase-industry-insights` | Segment direction, account-to-territory mapping, reproducible labels, prospecting handoff | Capital Trends owns investment capital analysis. Industry Insights owns GTM segment selection; funding momentum is not proof of buyer demand. |

Preserve recognizable display names. Proposed prefixed directory names follow `CONTRIBUTING.md`; they are not a requirement to rename the user-facing products. Test routing across all ten skills together, especially “prepare a brief,” “watch these accounts,” and “map fintech.”

## Material gaps and required changes

### 1. Activation and scope

All five incoming descriptions activate on generic sales language. The production skills require explicit Crunchbase selection or continuation of an active Crunchbase workflow. Add that same source-selection boundary and explicit neighboring-task exclusions. Keep useful generic examples only inside that boundary.

Replace silent material defaults with a concise proposal that the user can accept. Reuse prior inputs and authorizations; do not ask again for cosmetic choices. Geography, employee range, scoring weights, account caps, lookback periods, and market interpretation can change the answer and need an agreed scope. For example, Prospect Finder currently imposes 51–1,000 employees, while Industry Insights chooses the closest meaning of an ambiguous industry and invites correction after running.

Ambiguous accounts must not acquire scores, tiers, contacts, or list membership until resolved. Independent resolved rows can proceed with explicit coverage disclosure. Preserve correction and rerun workflows, but fix identity before downstream calculation.

Evidence: incoming `prospect-finder/SKILL.md` Inputs and Clarification contract; `industry-insights/SKILL.md` Clarification contract; `account-prioritizer/SKILL.md` clarification rule 4. Production standard: [contribution guidelines](../CONTRIBUTING.md) and [entity resolution](../skills/crunchbase-company-tearsheet-generator/references/entity-resolution.md).

### 2. Retrieval and tool contracts

Adopt the existing resolver-first, scoped-profile, live-schema, pagination, and bounded-error patterns. Resolve actual connected tool names rather than assuming a host prefix. Query examples are examples, not permanently verified operator contracts. Separate optional field absence from authentication, authorization, and service errors; a missing schema entry alone does not establish why access is unavailable.

Industry Insights explicitly calls `cb_expert_query_answer`; Prospect Finder's output references `cb_expert_build_search`. These conflict with the current skills' restriction to the entity resolver as their only expert tool. Rebuild aggregation and search-link behavior around supported structured retrieval, with complete denominators. If a required outcome cannot be supported, defer that feature and state the limitation rather than quietly adding an expert-tool exception.

Fix Account Signals's instruction to paginate only when `count` equals the page limit. Continue while the reported total exceeds retrieved unique rows, with cursor and duplicate handling. An agreed cap must be described as a cap; “top 1,000” requires ranking the agreed complete candidate pool, not merely the first retrieved subset.

Remove automatic filter relaxation after empty results. Diagnostic counts may identify a restrictive filter, but returned matches must retain the agreed filters until a scope change is accepted. Align web fallback with the production source policy: use external research when requested, with attribution, rather than automatically filling Crunchbase gaps from another source.

Evidence: incoming `account-signals/references/data-recipe.md:43` accepts the first equal-name autocomplete result; line 64 contains the pagination defect. `industry-insights/SKILL.md` procedure 3 uses the expert query tool. Production standard: [query core](../skills/crunchbase-market-map-builder/references/query-core.md) and [MCP requirements](../MCP-REQUIREMENTS.md).

### 3. Evidence and calculations

Retain the strong separation of observed facts, seller-fit hypotheses, and suggested wording. Replace blanket instructions never to mention missing or incomplete data with the production output contract: canonical links, as-of date, observed limitations, coverage, and unknown values. Concise cards may omit empty optional sections; omission must not hide a limitation that changes a ranking or conclusion.

Remove claims that predicted fundraising means budgets will arrive. Keep predictions attributed, dated, and distinct from an observed financing event or confirmed purchasing intent. Keep deterministic scores, but describe what they measure rather than calling them validated purchase likelihood or true ICP fit.

Two isolated checks reproduced issues in Prospect Finder on a fixed date of November 5, 2026:

| Input | Current result | Required behavior |
| --- | --- | --- |
| No growth, heat, or funding evidence | Overall score 0, same as known-zero growth and heat | Preserve unknown versus zero; apply an explicit coverage and score-eligibility policy. |
| Series A dated January 1, 2027 | 100 funding-factor points and overall score 30 | Reject or quarantine future observed-event dates; award no historical recency points. |

The first behavior retains null component values but collapses them in the overall score. Define score eligibility before choosing whether partial evidence yields an unscored row or a visibly provisional result; do not silently renormalize weights. Preserve the existing weights as a candidate rubric, subject to documented review, rather than changing commercial policy incidentally while fixing code.

Separate ICP eligibility from activity score. Prospect Finder currently calls the output “best matches” while requiring clearly poor-fit businesses to remain in the list. Either apply an auditable eligibility review before ranking eligible companies, or explicitly deliver unreviewed candidates. Preserve score reproducibility without implying that a high activity score establishes product fit. Resolve discovery overlap explicitly: Finder establishes a new universe, Prioritize scores an established universe, and Account Signals monitors it; any prediction-feed discovery exception needs its own routing cases.

Evidence: incoming `prospect-finder/scripts/score_prospects.py:181–215`; `prospect-finder/references/output-template.md:35` forbids an as-of date; `industry-insights/references/output-format.md:25,35` equates predicted funding with arriving budgets.

### 4. CRM, state, and writes

Keep CRM read-only and preserve the distinction between internal relationship history and external company evidence. Discover connector capabilities before claiming support. Document separate required and optional dependencies for Crunchbase, CRM, calendars, file processing, and recurring tasks.

Strengthen CRM identity matching: Account Brief's connector reference currently uses latest activity to break ties and illustrates substring website matching (`references/crm-connector.md:17,29`). Require corroborated company identity and the correct CRM account ID before using relationship history. Paginate history or disclose bounded retrieval; a query capped at ten deals cannot substantiate “every open deal.” Treat CRM text and tool-returned content as data, never instructions.

Make seller context and handoffs portable: versioned input schemas, provenance, explicit file selection when multiple candidates exist, and a documented fallback when persistent storage is unavailable. Do not assume a working-folder file or memory is available in every host. Define first-run baselines, event-date versus observation-date semantics, idempotent reruns, and state updates only after a complete successful run.

Require deterministic helpers for ranked or stateful outputs; if a host cannot execute them, offer only a clearly scoped unranked alternative or stop dependent work. Account Signals currently allows hand ranking while its scheduled state depends on script execution. Maintain the five CRM-export copies from one source or enforce parity checks while keeping installed packages self-contained.

Retain list saving only when requested. Apply the production preview and membership-verification pattern without demanding redundant approval for already-authorized actions. Separate local CRM export generation from permission to update a CRM. Recurring setup should use supported host capabilities when available and should not be claimed as configured merely because a prompt was drafted.

### 5. Evaluation and packaging

Use the incoming 45 prompts as scenario seeds, not as release evidence. The incoming suite runs against live data, has no paired no-skill control, and uses a model grader. Its `status_of` can pass empty criteria, `Pass*` includes unclear judgments, and reporting skips missing transcripts or grades. These behaviors do not satisfy the existing fail-closed release gate.

Add a GTM suite to the repository evaluator. Preserve its frozen artifacts, stateful fixtures, actual tool-effect checks, resumed clarification turns, paired no-skill comparisons, scenario-family splits, repeated trials, and human adjudication. Rewrite criteria that reward silent defaults or concealed limitations. Replace personal pilot context with synthetic personas and clearly fictional CRM records before committing public fixtures.

The incoming README references older per-skill calculator tests that are absent from this bundle; recover or recreate them rather than treating them as passed. Do not execute the incoming live harness unchanged: it uses permissive execution and a tool denylist, and its grader sees insufficient artifact and tool-result content to establish factual correctness.

Each incoming ZIP lacks the repository's license notices, release version, and optional Codex metadata. Add required notices after confirming provenance and contribution rights. Keep each skill independently installable, bundle only used resources, and use the existing shared version and release builder. Optional `agents/openai.yaml` improves discovery but is not a cross-host runtime requirement.

Evidence: incoming `Eval suite/suite.py:354–374,387–388,417–421`; local [evaluation methodology](../evals/METHODOLOGY.md), [evaluation guide](../evals/README.md), and [release builder](../scripts/build_releases.py).

## Implementation sequence

| Stage | Deliverable | Exit condition |
| --- | --- | --- |
| 1. Freeze contracts and scenario matrix | Shared GTM decisions for routing, scope, identity, evidence, partial data, scoring eligibility, writes, and state; source inventory | Every skill has positive, negative, overlap, missing-input, and failure cases. Required versus optional dependencies are explicit. |
| 2. Establish one vertical slice | Port Account Brief first using Tearsheet's retrieval and evidence patterns; preserve seller-specific output and read-only CRM context | End-to-end replay covers first meeting, follow-up, missing seller, ambiguous company, missing CRM, and connector failure. |
| 3. Port the paired scoring workflows | Account Prioritizer and Prospect Finder together, using one maintained scoring specification and equivalence checks | Same normalized evidence and agreed rubric produce the same base score across both skills. Unknowns, future dates, exclusions, caps, ties, and corrections have tests. |
| 4. Port account monitoring | Account Signals retrieval, ranking, histories, output, and durable state | Complete pagination, deduplicated events, no unsupported new-signal claims, and no state advancement on failure. |
| 5. Rebuild segment retrieval | Industry Insights structured retrieval and aggregation, territory assignments, handoff schema | Labels are traceable to an agreed universe and complete denominators; overlapping segments and partial coverage are handled correctly. |
| 6. Integrate and release | GTM suite, all-ten-skill routing checks, workflow guide, catalog, tool requirements, metadata, archives | Offline checks, reviewed replay gate, read-only live integration, and representative host installation checks pass. |

Use small reviewable changes per stage. Keep shared reference content consistent while bundling it into each standalone skill; avoid a new runtime dependency on another installed skill. Do not advertise unimplemented capabilities in the catalog. A backward-compatible expansion suggests a minor release under the repository policy; select the version only when the release scope is settled.

## Acceptance checks

- **Routing:** all ten skills coexist; unrelated requests do not activate GTM skills; continuation retains the correct workflow and supplied inputs.
- **Clarification:** material defaults are disclosed and accepted, ambiguous identities stay unresolved, and supplied answers resume work without repeated questions.
- **Retrieval:** live contract resolution, zero results, multiple pages, duplicates, optional-field absence, unavailable tools, validation recovery, authentication, permission, and usage-limit failures.
- **Untrusted content:** hostile instructions embedded in company records, CRM history, and uploaded files cannot alter scope, source policy, or write authorization.
- **Calculations:** independently specified examples; unknown versus zero; future and boundary dates; valid numeric ranges; score parity; stable tie-breaking; deduplication; event histories; segment denominators and overlap.
- **Outputs:** canonical links, as-of dates, coverage, limitations, traceable reasons, CRM provenance, and visibly hypothetical seller fit. No implied buying intent from predictions.
- **State and writes:** first run, unchanged run, changed criteria, interrupted run, retry, and corruption recovery; no unrequested writes; verified list membership after authorized writes.
- **Evaluation gate:** missing artifacts and pending judgments cannot pass; run the frozen suite with at least three repetitions and adjudicated paired baseline evidence under the current policy. Protect existing research workflows with regression checks.
- **Integration and release:** separately document read-only live checks for actual tool contracts and entitlements; validate complete standalone archives, local links, notices, version synchronization, and representative Codex and Claude installations. Replay success alone is not a production claim.

## Decisions to settle during implementation

The recommended defaults are: retain all five workflows; use explicit Crunchbase activation; preserve the current scoring formula initially but with explicit evidence eligibility; keep CRM read-only; and treat recurring operation as a host-dependent extension. Confirm the intended first-release entitlement coverage and whether all five ship together or Account Brief ships first after meeting the same gates.

No production skill was edited or installed during this assessment, and no live Crunchbase evaluation was run. The source archives remain unchanged. Source references above use archive-relative paths so findings remain traceable after temporary extraction files are removed.
