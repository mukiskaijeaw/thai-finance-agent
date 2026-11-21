# Portable package validation — 2026-11-14

| Suite | Actual result |
| --- | ---: |
| Core Python engine/workflow tests | 209 PASS |
| Local dashboard/chat/HTTP tests | 29 PASS |
| Comparison-state tests | 4 PASS |
| Companion, goal and purchase DOM simulations | 24 PASS |
| Generated synthetic simulator DOM tests | 9 PASS |
| Optional PNG renderer tests (Pillow/Thai fonts available) | 9 PASS |
| Total | 284 PASS |

Tests ran against this prepared checkout. Persistent goal writes used temporary databases. No real provider/ledger/profile/receipt was copied or read. No product search API, LLM, purchase or transfer was invoked. Optional PNG support needs Pillow and suitable Thai fonts; it is not required by the core or dashboard.

DOM tests simulate events; they do not certify inline rendering in every Codex version. Browser UI was exercised in the original local source before packaging; the packaged dashboard was validated through HTTP tests. No claim of measured token savings. Standard skill-validator execution remains unavailable in this environment because optional PyYAML is absent.

Expense-analysis update: verified empty state without preset categories, user-defined monthly totals, percentage reductions, explicit subscription periods, invalid/duplicate input handling and no ledger writes. Browser checked custom category 800 with 20% reduction = 160/month, then removed the temporary test input. Dashboard financial Demo fixtures remain synthetic and isolated.

## Review fixes — current working tree (not committed)

- PASS: core Python 213; dashboard HTTP/chat 31; companion/goal/purchase DOM 27; legacy simulator DOM 9; comparison 4; optional PNG renderer 9. Total 293 passing tests.
- PASS: browser UI with an isolated temporary Demo store: Daily slider; 2,500 to 8,125 price slider and goal form; reviewed creation of a synthetic 1,000 goal and calendar; Thai travel status and local slider.
- PASS: synthetic 14 Nov 2026 through 14 Dec 2026, available 6,500, no goals/extra obligations: 31 inclusive days and 209.67/day for Daily and price simulation. No actual transaction rows or financial profile values were used.
- PASS: five-category synthetic travel fixture: 3,125 combinations; 61 distinct totals; serialized state comparison 711,193 bytes repeated versus 293,696 bytes shared. Comparison covers simulation state data, not total app size or model usage.
- FAIL: none in the final runs; initial stale expectations were corrected and the full tests rerun.
- NOT TESTED: actual Codex inline host interaction; DOM stubs do not prove host delivery.
- NOT CONNECTED: actual Pillar 1 dashboard, Pillar 5 subscriptions/bills, team shared-goal source, and The Money Journal. Team Walkthrough HTML and the relevant agent_state.json/shared-goal/Journal contracts were not found; no schema was guessed. The Pillar 1 CSV header was inspected without reading transaction rows.
- No real ledger, profile, receipt or user goal store was read or written; no purchase, transaction, commit or push was made. Browser mutations used a temporary Demo store only.

Changed files for this review:
- .agents/skills/shopping-agent/scripts/companion_engine.py, purchase_flow.py, goal_renderer.py, shopping.py
- .agents/skills/shopping-agent/assets/companion-inline.html, purchase-flow-inline.html, goal-planner-inline.html
- .agents/skills/shopping-agent/tests/test_companion.py, test_cycle_regressions.py
- .agents/skills/shopping-agent/component_tests/test_companion_dom.cjs, test_goal_dom.cjs, test_purchase_dom.cjs
- dashboard/app.js, dashboard/chat.js, dashboard/server.py, dashboard/test_server.py
- TEST_RESULTS.md
