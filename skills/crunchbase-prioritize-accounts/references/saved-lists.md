# Saved Lists

Use saved lists as persistent company universes only when the user explicitly authorizes a list action.

## Read operations

- Use `cb_list_query` to find available lists and inspect names, IDs, counts, ownership, and modifiability.
- If similar names exist, show the candidates and ask the user to choose.
- Use `cb_list_get` for membership display or reconciliation, following `next_after_id` until complete.
- Use `identifier in_list [<list_id>]` for organization searches and the corresponding live-supported `in_list` predicates for funding rounds or acquisitions.

## Write authorization

A request to search, analyze, compare, propose, or monitor companies is read-only. Write only when the user explicitly asks to save or create a list, append entities, or update membership. Before the first write, show:

- Proposed list name
- Canonical linked companies
- Confirmed, ambiguous, and unresolved counts
- Whether an existing list has the same or a confusingly similar name

If the user already explicitly requested the named write and the canonical set is unambiguous, this preview may be immediately followed by the write.

## Create and append

1. Query existing lists before creating one.
2. Reuse an exact intended list only when the user requested an append or update and the list is modifiable. If the user requested creation, create a collision-free versioned list even when an exact existing list is empty.
3. Otherwise create a collision-free versioned name such as `<purpose> — <YYYY-MM-DD> v2`.
4. Add only confirmed organization UUIDs.
5. Read the list back and reconcile requested, confirmed, submitted, and persisted entities.
6. Report the list ID, final name, final count, and any entity whose outcome requires attention.

After reconciliation succeeds, stop calling tools and render the final result immediately. Do not run a post-write audit, discovery query, or enrichment pass.

Do not repeat an add call blindly after an uncertain response. Read the list first, compute the remaining entities, and submit only that authorized remainder at most once. Read back after that repair; if requested entities are still missing, report actual membership and the unresolved remainder rather than looping. Authentication, permission, or metering failures remain terminal.

## Remove or replace

A request to remove a member authorizes an in-place removal only. It does not authorize creation of a replacement list. When in-place removal is unavailable, preview the replacement and wait for the user's explicit approval in a later turn before any `cb_list_create` or `cb_list_add_entities` call.

For every named member in a remove or replacement request, resolve the company to a canonical organization UUID with `cb_expert_resolve_entity` before computing the retained set or previewing a replacement. A supplied name alone is not sufficient; stop and ask when several candidates remain credible.

When the available tools cannot remove members in place:

1. Identify the exact list with `cb_list_query`.
2. Resolve every named member as specified above.
3. Read the current membership completely with `cb_list_get`.
4. Compute the retained and added sets by UUID.
5. Preview the proposed replacement.
6. Create a new versioned list after explicit authorization.
7. Add the revised set and reconcile it.
8. Identify the prior list as the preceding snapshot without claiming it was deleted or deactivated.

Saved-list membership is not a historical snapshot of organization fields. Keep membership version and monitoring baseline separate.
