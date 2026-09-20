# Housekeeping sweeps

Append-only record of `scripts/maintenance/housekeeping.py --apply` runs under docs/testing/retention-policy.md. Deleted logs remain indexed in test-results.md and recoverable from git history.

| UTC date | Compressed | Deleted | Log volume after (MB) | gc | Breaches |
|---|---:|---:|---:|---|---|
| 2026-09-03 | 821 | 287 | 61.1 | yes | log volume 111.3 MB > 25.0 MB; loose objects 310 MiB > 50 MiB; docs/testing/attempts.md 17215 lines > 6000 |
| 2026-09-06 | 170 | 39 | 54.9 | no | non-gating log volume 29.7 MB > 25.0 MB; docs/testing/attempts.md 19826 lines > 6000; PROJECT_PLAN.md 9786 lines > 9000 |
| 2026-09-13 | 233 | 230 | 32.6 | yes | non-gating log volume 30.1 MB > 25.0 MB; loose objects 78 MiB > 50 MiB; docs/testing/attempts.md 17981 lines > 6000; PROJECT_PLAN.md 9698 lines > 9000 |
| 2026-09-20 | 227 | 273 | 32.4 | yes | loose objects 90 MiB > 50 MiB |
