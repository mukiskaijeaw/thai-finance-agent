# Portable package validation — 2026-11-14

| Suite | Actual result |
| --- | ---: |
| Core Python engine/workflow tests | 209 PASS |
| Local dashboard/chat/HTTP tests | 18 PASS |
| Comparison-state tests | 4 PASS |
| Companion, goal and purchase DOM simulations | 23 PASS |
| Generated synthetic simulator DOM tests | 9 PASS |
| Optional PNG renderer tests (Pillow/Thai fonts available) | 9 PASS |
| Total | 272 PASS |

Tests ran against this prepared checkout. Persistent goal writes used temporary databases. No real provider/ledger/profile/receipt was copied or read. No product search API, LLM, purchase or transfer was invoked. Optional PNG support needs Pillow and suitable Thai fonts; it is not required by the core or dashboard.

DOM tests simulate events; they do not certify inline rendering in every Codex version. Browser UI was exercised in the original local source before packaging; the packaged dashboard was validated through HTTP tests. No claim of measured token savings. Standard skill-validator execution remains unavailable in this environment because optional PyYAML is absent.
