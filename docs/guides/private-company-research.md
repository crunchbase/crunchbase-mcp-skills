# Private-company research workflows

This guide covers the first collection in Crunchbase MCP Skills. The five workflows support company research, funding analysis, and saved-list operations. Their private-company scope belongs to these skills, not to the repository as a whole.

## Choose a workflow

- **Landscape:** “Use Crunchbase to map software for independent dental practices. Segment companies by the workflow they serve.”
- **Funding:** “Use Crunchbase to screen European seed rounds in climate software announced in the past 30 days.”
- **Company brief:** “Use Crunchbase to prepare a meeting brief on Canva, including financing, team, peers, and questions to test.”
- **Capital analysis:** “Use Crunchbase to analyze capital intensity across this confirmed company set: [paste private-company names or Crunchbase URLs]. Compare the trailing 12 months with the preceding 12 months.” Replace the bracketed text with your company set.
- **Saved list:** “Use Crunchbase to inspect my ‘Climate software’ list and summarize its current membership.” Replace the example list name with your own.

To save a newly discovered landscape, include “save the reviewed companies to a new list named …” in the landscape request. To append companies to an existing list, name the list and the companies explicitly. The agent previews canonical identities before the write and checks persisted membership afterward.

## Required inputs and questions

These skills activate for an explicit Crunchbase request, a selected Crunchbase source, or a continuation of an active workflow.

| Workflow | Essential input |
| --- | --- |
| Company brief | A company name, supplied domain, or previously resolved identity |
| Landscape | A usable thesis and any choices that materially change the screen |
| Funding signals | A theme or explicitly broad screen, a review window, and material screening choices |
| Capital intensity | A user-confirmed company universe and any material unresolved analysis scope |
| Saved lists | The intended operation and its required list or company identifiers; explicit intent for writes |

When a missing input would materially change the companies selected, the analysis, or a saved-list action, the agent asks one focused question covering the unresolved essentials. It reuses answers and authorizations already supplied, and offers concrete options when helpful. It asks the user to choose between company or list identities only when credible alternatives remain after minimal resolution.

Proposed defaults require acceptance. An unspecified geography or stage is not silently interpreted as unrestricted, and an omitted funding window is not silently interpreted as 30 days. An explicit request for a broad screen is sufficient to proceed broadly. A general company brief does not require a meeting-purpose questionnaire.

For example, “US, pre-seed through Series A, operating private companies with less than $15 million raised” is a valid mandate when requested. It is not an automatic filter applied to every landscape.

## Results and boundaries

A first-pass landscape is bounded and labeled with what was retrieved and reviewed. An explicit complete request requires the relevant pagination; a service limit or incomplete retrieval is disclosed. Confirmed-list results are never presented as whole-market estimates.

Outputs distinguish retrieved facts, calculations, interpretation, and suggested actions. A dash means no value was returned for that field. Material limitations—such as partial retrieval, unresolved identities, or excluded amounts—are stated with their effect on the conclusion. An absent event record is not evidence that the event did not occur.

Company briefs, funding screens, capital analysis, and list inspection or monitoring are read-only. A landscape can save its reviewed set when explicitly requested. Saved-list changes require the requested operation, resolved identities, a preview, and membership reconciliation. A request to remove companies does not authorize creating a replacement list; if in-place removal is unavailable, the agent proposes a replacement and asks for approval.

A company brief is a meeting-preparation aid, not full commercial, technical, or investment diligence. Funding screens present review priorities; an investment verdict requires a decision rubric supplied by the user.

See [tool requirements](../../MCP-REQUIREMENTS.md) for connection capabilities and calculation input handling.
