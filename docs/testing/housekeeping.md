# Housekeeping sweeps

Append-only record of `scripts/maintenance/housekeeping.py --apply` runs under docs/testing/retention-policy.md. Deleted logs remain indexed in test-results.md and recoverable from git history.

| UTC date | Compressed | Deleted | Log volume after (MB) | gc | Breaches |
|---|---:|---:|---:|---|---|
| 2026-09-03 | 821 | 287 | 61.1 | yes | log volume 111.3 MB > 25.0 MB; loose objects 310 MiB > 50 MiB; docs/testing/attempts.md 17215 lines > 6000 |
