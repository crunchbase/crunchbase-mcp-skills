# Crunchbase tool requirements

Connect and authenticate Crunchbase through the host agent before invoking these skills. Host-specific prefixes may differ; the tool basenames and capabilities below must be available.

| Capability | Tool basenames | Needed for |
| --- | --- | --- |
| Live schema and search | `cb_reference`, `cb_search_query` | Structured searches and current field/operator contracts |
| Identity resolution | `cb_expert_resolve_entity`, `cb_entity_autocomplete` | Canonical company identities and category/location lookup |
| Scoped profiles | `cb_entity_get` | Briefs and targeted enrichment with explicit fields and cards |
| Read saved lists | `cb_list_query`, `cb_list_get` | List selection, membership retrieval, and write reconciliation |
| Write saved lists | `cb_list_create`, `cb_list_add_entities` | Explicitly requested creation or additions |

Each workflow needs only the capabilities it uses. A company brief, for example, does not require list-write permission. Capital analysis is read-only even when its universe comes from a saved list. A landscape can save its reviewed set when explicitly requested.

Use the connector's current reference responses for field names, operators, enum values, identifier forms, cards, and pagination. Successfully resolved contracts can be reused during the session. Responses must preserve canonical identifiers, profile URLs, pagination information, and requested fields. Do not substitute an unrelated search service or infer unavailable fields.

Authentication, authorization, and usage limits belong to the connector and the user's account. Report a blocking connection, permission, usage-limit, or service error clearly. Keep credentials and account-specific connection settings outside skill directories.

The bundled Python helper accepts normalized JSON, as documented in each copy of `scripts/derive_metrics.py`: ISO dates, organization/round UUIDs, and numeric USD values or null. Convert structured connector date and money values into this form before calling it. Preserve any source-date precision in the analysis and do not imply precision the source does not provide.
