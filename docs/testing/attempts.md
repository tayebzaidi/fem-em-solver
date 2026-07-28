# Attempt journal — scheduled implementer runs

Append-only. One entry per scheduled run, successful or not. Written by the
implementer runs (docs/automation/implementer-run.md); the daily review
(docs/automation/daily-review.md) is the reader. Do not edit prior entries.

Entry format:

```
## <UTC timestamp> — <CHUNK-ID> — <complete|incomplete|blocked|anomaly>
- Tried:
- Result / measured:
- Logs: <docs/testing/logs/ filenames>
- Branch (if parked): attempt/<CHUNK-ID>-<UTC timestamp>
- Next-attempt hypothesis:
```

---
