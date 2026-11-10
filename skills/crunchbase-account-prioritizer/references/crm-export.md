# CRM export normalization

Read attached or explicitly named CSV/XLSX exports only within the requested scope. The bundled `scripts/crm_export.py --input FILE --out-dir DIR` normalizes account, opportunity/deal and contact reports. Multiple `--input` files may be joined; optional `--owner` requires the exact intended owner name and `--open-only` restricts to open deals. XLSX needs installed `openpyxl`; otherwise request/export CSV without installing silently.

Use canonical CRM IDs first, exact supplied domains second. Never join two conflicting CRM IDs or two different supplied domains merely because names match. Name-only rows remain separate until identity is resolved. Retain source input rows and report ambiguous/unlinked records rather than inventing associations. A CRM ID is not a Crunchbase UUID: resolve the company before enrichment. Deal stage labels must be known; custom stage IDs need a user/schema mapping before interpreting won/lost/open. Dates in unambiguous ISO format are preferred; reject ambiguous numeric date formats instead of silently swapping month/day.

The helper creates `crm-accounts.csv`, optional `crm-contacts.csv`, and `crm-domains.txt`. It drops phone/email/address fields from exports and escapes formula-like text. Preserve counts and unlinked rows. CRM history describes the user's records and may inform an approach, but never changes the Crunchbase-derived rank. Prospecting excludes the whole authorized CRM set unless the user specifies otherwise; owner filtering is appropriate only for a rep-specific prioritization book.

Exports are local artifacts. Do not mutate Salesforce/HubSpot, send outreach, or claim a CSV was imported. Keep source provenance and private records out of public evaluation fixtures.

## Monetary evidence

`crm-deals.json` (`crm-deals/v1`) retains each included deal's original amount text, original currency text, parsed amount, normalized explicit three-letter currency, and account identity. Never interpret an absent/invalid currency or bare `$` as USD. Converted amount columns have unknown currency unless their destination currency is established separately; the helper does not infer it from the record's original currency.

`Open amount` and `Open amount currency` are populated only when every open deal has a parsed amount and the same explicit currency. Otherwise the total is blank, with `Open amount status` identifying missing amounts, unknown currency, mixed currencies, or no open deals. No FX conversion or cross-currency sum is performed. Use the per-deal evidence for mixed or incomplete books; never replace a blank total with zero.
