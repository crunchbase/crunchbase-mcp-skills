# Crunchbase MCP requirements

Connect and authenticate Crunchbase through the host agent before invoking a skill. Requirements are specific to each workflow; the repository does not require every skill to use the same tool set. Host-specific tool prefixes may differ, while the tool basenames and capabilities used by a skill must be available. Resolve each basename to the actual fully qualified tool name exposed by the connected Crunchbase server; do not guess a server prefix. Host metadata such as `agents/openai.yaml` does not configure Claude’s MCP connection.

## Current private-company research collection

| Capability | Tool basenames | Needed for |
| --- | --- | --- |
| Live schema and search | `cb_reference`, `cb_search_query` | Structured searches and current field/operator contracts |
| Identity resolution | `cb_expert_resolve_entity`, `cb_entity_autocomplete` | Canonical company identities and category/location lookup |
| Scoped profiles | `cb_entity_get` | Briefs and targeted enrichment with explicit fields and cards |
| Read saved lists | `cb_list_query`, `cb_list_get` | List selection, membership retrieval, and write reconciliation |
| Write saved lists | `cb_list_create`, `cb_list_add_entities` | Explicitly requested creation or additions |

Each workflow needs only the capabilities it uses. A company brief does not require list-write permission. Capital analysis is read-only even when its universe comes from a saved list. A landscape can save its reviewed set when explicitly requested.

The current saved-list workflow does not assume an in-place removal tool. If removal is unavailable, creating a replacement requires a preview and the user's explicit approval of that alternative.

## Contracts and access

Use the connector's current reference responses for field names, operators, enum values, identifier forms, cards, and pagination. Successfully resolved contracts can be reused during the session. Responses must preserve canonical identifiers, profile URLs, pagination information, and requested fields. Do not substitute an unrelated search service or infer unavailable fields.

Authentication, authorization, and usage limits belong to the connector and the user's account. Report a blocking connection, permission, usage-limit, or service error clearly. Keep credentials and account-specific connection settings outside skill directories.

## Local helper runtime

Skills that include `scripts/derive_metrics.py` require Python 3.9 or later. The helper accepts normalized JSON: ISO dates, organization/round UUIDs, and numeric USD values or null. Convert structured connector date and money values into this form before calling it. Preserve any source-date precision in the analysis and do not imply precision the source does not provide.

The company-brief skill has no bundled calculation helper. Future skills should document their own runtime and tool requirements here instead of inheriting unrelated requirements from the initial collection.

## GTM collection

The five GTM skills are independently installable. Each workflow requires only the data capabilities listed below.

| Workflow | Required data capabilities | Optional capabilities |
| --- | --- | --- |
| Account Brief | Named-entity resolution, scoped organization profiles and relevant funding/product records | Read-only CRM history, calendar context when requested, professional people records, peers and insights |
| Prospect Finder | Structured organization searches, canonical identity, scoring observations | Micro-industries, organization similarities for look-alikes, products for seller fit, saved-list reads and explicitly requested writes |
| Account Prioritizer | Canonical account book and structured scoring observations | Saved-list reads, CRM export ingestion, fund closes for investor accounts, explicitly requested reviewed-list saves |
| Account Signals | Canonical book, selected event collections, prediction histories when tracked, layoff records for its documented ranking penalty | Products, professional people, CRM context, durable recurring state |
| Industry Insights | Micro-industry definitions, complete organization universe and funding-round records | Funding prediction tiers, market insights, account-to-territory assignment, durable recurring state |

These capabilities use the existing basenames `cb_reference`, `cb_expert_resolve_entity`, `cb_entity_autocomplete`, `cb_entity_get`, and `cb_search_query`. Saved-list paths use the existing list tools and reconciliation contract. Do not introduce another expert tool for GTM aggregation. Resolve fields, operators, collections and entitlements from the actual connected session; a schema lookup alone does not establish a subscription diagnosis.

Workflow-specific collections can include `micro_categories`, `products`, `org_similarities`, `funds`, `funding_predictions`, `acquisition_predictions`, `growth_insights`, `market_insights`, `key_employee_changes`, `product_launches`, `addresses`, `partnership_announcements`, and `layoffs`. Use only collections needed for the accepted scope. Required unavailable evidence blocks the corresponding calculation or leaves rows explicitly unscored; optional omissions need decision-relevant disclosure. Preserve returned canonical URLs; not every non-profile entity has a public URL.

Use Python 3.10+ as the common GTM runtime, including CRM ingestion. Industry Insights's calculation helper alone also supports Python 3.9+. CSV/JSON workflows use the standard library; optional XLSX/XLSM CRM ingestion requires openpyxl, otherwise use CSV. Normalize structured date and money values as each schema specifies, retaining null, zero and date precision. Never pass raw non-USD amounts as USD.

CRM/calendar adapters are host-dependent, read-only additions discovered at runtime, not guaranteed Crunchbase tools. Local CRM exports do not authorize CRM mutation. Recurring-task setup, execution, delivery and durable state are separate host capabilities; do not claim persistent operation where the host lacks one. Automated replay uses synthetic records and local state only; live connection checks are separately documented.
