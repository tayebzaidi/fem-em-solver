# Push notification policy (scheduled sessions)

Scheduled review sessions may send the human operator a push notification via
the `PushNotification` tool. Notifications interrupt a person; the budget is
**hard-capped at 2 per rolling 7 days**, enforced by the ledger below. This
file is the single authority on when to send and the record of what was sent.

## What warrants a notification

Only events that are *blocked on the human operator* or that mean the
automation cannot help itself:

1. **Ansys benchmark awaiting replication** — the weekly review commissioned
   or updated an `examples/ansys_benchmarks/<case>/` and the next step is the
   operator running it in AED (PROJECT_PLAN §5.4).
2. **Automation outage** — two consecutive scheduled cycles failed, stalled,
   or were blocked (accumulating `recovered/*` branches, Docker service down,
   repeated preflight trips), i.e. the self-healing described in
   implementer-run.md step 1 is not working.
3. **A §4/§10 gate that only the operator can clear** — e.g. a phase
   completion whose definition of done names a human verification step.

Everything else — chunk completions, review summaries, negative results,
parked attempts — goes on the dashboard's **Waiting on you / Recent activity**
sections, never into a notification.

## Procedure (for the sending session)

1. Confirm the event matches a category above.
2. Count ledger rows dated within the last 7 days. **2 or more ⇒ do not
   send**; record the event under "Suppressed" instead and put it at the top
   of the dashboard's Waiting-on-you list.
3. Send one message, ≤ 200 characters, leading with the action needed
   (e.g. "AED replication needed: ansys_benchmarks/loop_air_64MHz ready —
   see dashboard").
4. Append a ledger row in the same commit as the rest of the session's work.

If the `PushNotification` tool is unavailable in a headless session, treat the
event as suppressed (dashboard only) and note the unavailability in the row.

## Ledger

| Date (UTC) | Session | Category | Message (abridged) |
|---|---|---|---|
| 2026-08-05 | interactive setup | test | Delivery test during notification-pipeline setup (does not count against the budget going forward; category "test" is reserved for pipeline checks) |

### Suppressed

*(none yet)*
