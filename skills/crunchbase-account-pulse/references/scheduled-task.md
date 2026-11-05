# State and recurring operation

Host scheduling is optional. Discover an actual scheduler only when the user asks for recurring monitoring. Record timezone, cadence, exact book, seller context, accepted signal/rubric/window/scope, state destination and output policy. Creating a prompt does not create a schedule. Do not send outreach or claim host persistence without confirmation. Unattended tasks use their accepted inputs; absent required inputs produce an actionable failure rather than new assumptions.

Run rank first without --write-state to inspect the proposed result. The first persistent run is a baseline with no alerts. Commit using the same accepted inputs and `--state <path> --write-state --out <result.json>` only when complete retrieval and valid evidence are established. The helper writes the result before atomically replacing state. Failure before successful output leaves the prior baseline unchanged. Do not reuse one state/output path concurrently; serialize runs per monitor.

State schema `pulse-state/v2` stores last_run, book, scope, scope_fingerprint, seen_events, predictions, acq_predictions and last_alerted. Its fingerprint includes canonical account UUIDs/tiers, selected signals, event/play windows, alert/play scopes, seller focus/buyer keywords and rubric version. Changed scope or a date before last_run is an error: create a new explicitly identified baseline, do not silently overwrite old history. Corrupt/legacy state is an error; preserve it for diagnosis and establish a fresh baseline only as a deliberate reset.

A valid rerun does not repeat events already seen or a prediction transition already recorded. Missing history is unknown, not evidence a prediction was previously negative. `--since` without state is a dated-window view, not verified since-last-run change. Event date and record-observation date remain separate; backfilled old events are not fresh occurrences. No state advancement is permitted after incomplete collections, mismatched counts, rejected invalid observations, terminal service errors, or output-write failure.

Without durable storage, offer a non-stateful evidence view with an explicit window; do not claim deduplicated monitoring. Without code execution, no ranking or stateful alerts are supported. Stay quiet when a successful recurring run finds no new actionable result unless the user asked for periodic status updates. Missing capability or a failed run is a meaningful notification.

The durable result is saved before the state commit and records state_commit_requested; its state_written is null until a commit is confirmed. The successful command result reports state_written; inspect the actual state file when reconciling a failure. The precommit artifact never claims a state write succeeded before it happened.

## Inclusive calendar windows

An N-day event or play window ending on the as-of date includes both endpoints: start = as-of − (N − 1) calendar days. Thus 60 days ending November 5, 2026 starts September 7, and a one-day window contains only November 5. Fetch using these exact boundaries; play windows are capped at the accepted event lookback. Explicit `--since` is a change-detection boundary, not an N-day event-window substitute.

All computed scores and individual components, including layoff penalties, require `pulse.py`, even in an unranked review. Without execution, report only raw evidence counts and limitations; do not describe a zero penalty as calculated.

Scope fingerprints now include `window_policy: inclusive-calendar-days/v1`. Earlier state is intentionally incompatible: preserve it, establish a newly authorized baseline at a new path, and do not compare or alert across that policy change. Formula weights and rubric version are unchanged.
