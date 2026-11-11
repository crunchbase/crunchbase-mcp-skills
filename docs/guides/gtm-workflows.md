# GTM workflows

These five skills support distinct sales tasks and share the same identity, evidence, and retrieval standards.

| Skill | Use it for | Example |
| --- | --- | --- |
| Account Brief | Sales meeting preparation and CRM-informed follow-ups | “Use Crunchbase to prepare my first meeting with Acme. I sell billing automation to software vendors; review developments in the last six months.” |
| Prospect Finder | New ICP and customer look-alike prospects | “Use Crunchbase to find US dental-software prospects with 11–250 employees. Exclude my supplied account list; rank the complete matched pool and show 20.” |
| Account Prioritizer | Consistent scoring of an existing book | “Use Crunchbase to tier all accounts in this CSV using the disclosed 40/30/30 rubric and A/B cutoffs of 70/50. Keep unknown evidence unscored.” |
| Account Signals | Dated signals across an established book | “Use Crunchbase to review this book for funding and leadership signals over the past 60 days. Include the documented layoff penalty; I sell billing automation.” |
| Industry Insights | Segment direction and territory assignments | “Use Crunchbase to compare these three sales segments worldwide across all company sizes. Use the two adjacent twelve-month windows and the documented direction rule.” |

Material missing scope is clarified before applying filters. Already supplied inputs and authorizations are reused. Explicit Crunchbase selection is required; the sales skills do not take over unrelated generic requests. The research collection remains responsible for investment landscapes, recent-round mandate screens, general private-company briefs, capital analysis, and saved-list management.

## Expected outputs

Account Brief separates returned facts, CRM history, seller claims, hypotheses, and suggested wording. It supports a concise brief, a paste-ready CRM note, and a versioned JSON artifact. It never sends outreach or writes CRM records.

Prospect Finder and Account Prioritizer share a versioned deterministic score. Growth, media attention and financing are review signals, not buying probability. Unknown positive-weight factors produce an unscored row; observed zero remains zero. Configurable weights and tier thresholds are explicit. JSON preserves source evidence and coverage, while CSV and supported import layouts preserve canonical and CRM identities. Generated import files are not a completed CRM update.

Account Signals retains the sourced event list, deterministic ranking, plays and prediction feeds. Missing required ranking inputs produce unranked evidence. Recurring comparisons establish a baseline first and advance state only after complete successful retrieval and output. A host must actually support scheduling and persistence before either is claimed.

Industry Insights uses complete structured organization and round records. It reports emerging/growing/steady/declining only for sufficiently sized segments with observed inputs and at least three comparable peers. Sparse or unknown evidence is explicitly unclassified. Territory membership can overlap; exclusive assignment requires an accepted deterministic policy. A prospecting handoff preserves agreed filters without authorizing a new search or outreach.

## Runtime and portability

Use Python 3.10+ for all GTM helpers as a common supported runtime, even where an individual helper supports an earlier version. CSV/JSON workflows use the standard library; optional XLSX/XLSM CRM ingestion requires openpyxl, otherwise use CSV. Each skill is self-contained; no other installed skill is required. Preserve the complete folder with references, scripts and license notices.

Connector metadata and capabilities are discovered at runtime. Optional CRM/calendar reads and recurring tasks depend on the host. Complete retrieval is distinct from complete real-world coverage. Source dates, canonical links, unknown values, and decision-relevant limitations remain visible.

Select schemas by their declared version and consult each bundled reference when integrating an existing automation. Do not pass legacy query-plan CLI arguments to the new scoring or Industry Insights helpers.

A handoff preserves context but does not automatically execute the next workflow. Normalize each receiving schema explicitly and retain the accepted market scope, seller context and authorization. Account Signals may require additional growth-tier evidence; a previously scored prospect can correctly remain unranked when that evidence is missing.
