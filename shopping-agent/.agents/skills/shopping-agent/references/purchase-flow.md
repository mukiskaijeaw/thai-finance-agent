# Purchase decision → confirmed product → optional goal

Use the existing search/effective_price/confidence, planning.fit, decision_policy.recommend, goal_engine and GoalStore. No new website/server/dependency. Production entry contains no product, price, image or deadline default; end-of-current-month is calculated only AFTER product confirmation. Tests contain synthetic examples; do not treat them as real offers.

## Entry and source identification

`shopping.py purchase --format json|markdown|inline` accepts JSON stdin. `--format inline --output <new-fragment.html>` uses the same assets/purchase-flow-inline.html. Bare menu click immediately returns action=entry UI. If the user already supplied a product/model/URL/photo, action=entry with intent `{product,budget?,image_attached?}` yields SEARCH_REQUIRED; skip form and research. The UI identifies image input as an attachment in the main chat, never an external upload field. A photo alone is not an expense or a search-upload authorization.

Action identify returns a search request state; Codex searches using PRODUCT_KEYS and existing tools, never financial inputs. Supply action=candidates with session, target attributes and sourced listings. Broad intent: up to four distinct products; exact=true requires HIGH model/SKU match with no conflicts and produces one candidate. Candidate listings use existing price/shipping/discount/checked/stock/evidence fields, plus optional variant/details/image_url/image_verified/image_source. Image must have verified HTTPS provenance. Separate user/photo identification evidence from listing match evidence; use existing confidence helper for both. No synthetic certainty percentages.

UI image elements attempt the verified source with no-referrer and fall back to the category icon/source link if host CSP blocks merchant images. Never download images to bypass host policy. An estimate is labeled approximate and cannot produce an affordability verdict. Backend checks evidence consistency, not the truth of a merchant's or agent's assertion.

## Sessions and transitions

- entry: blank form or SEARCH_REQUIRED from supplied intent.
- candidates: sourced offers -> CONFIRM; no financial read.
- select: product_id from candidates plus confirmed=true -> selected product and DECISION. Click on “ใช่ รุ่นนี้แหละ” authorizes product selection only.
- select_and_evaluate: selection then the same evaluation below; if finances missing, show NEED_MORE_INFO for confirmed affordability without invented zeros, and continue sourced alternatives or conditional budget guidance.
- reject/search_again: clear selected product; request focused clarification/new research.
- evaluate/change_date/buy_today/goal_preview/start_goal: reuse the selected listing; do not search again while valid. If stale or incomplete, ask/refresh that evidence. “หาราคาที่ถูกกว่า” explicitly requests a fresh comparison for the SAME variant; do not silently change product.
- change_product resets entry; skip produces SKIP_PURCHASE without purchase, watchlist or goal writes.

Session is caller-owned JSON: version, stage, intent, candidates, selected_product, selection_confirmed. public_session excludes report/profile/cash/debt. UI saves only this product state via host widgetState; model delivery is best-effort, so action messages include it too. Restore picks the current candidate by ID, never replaces fresh quotes with older saved pricing. If host state is missing use the latest explicit user-confirmed selection in this conversation. Do not persist financial profiles in widget state or external queries.

## Financial evaluation

Pass current confirmed `profile`, cycle `budget`, optional forecast, coverage and sourced policy `context` as in planning-contract.md/decision-policy.md. CLI optionally uses selected --finance-dir only for financial actions and never in synthetic mode. Existing unconfirmed zero profile remains unknown. Read provider rules before provider access. Read GoalStore automatically so callers cannot omit competing goals. Goal saved balances and scheduled current-cycle contributions are protected once; only the extra reserve delta is passed into existing planning.fit. Optional user budget is respected as a cap, not invented available cash.

Recommendation remains one of BUY_NOW/BUY_WITH_CAUTION/WAIT_AND_SAVE/CHOOSE_ALTERNATIVE/SKIP_PURCHASE/NEED_MORE_INFO. Confirmed model is not confirmed stock/suitability. Missing purpose/necessity/readiness stays NEED_MORE_INFO; affordable alone never forces BUY_NOW. Alternatives must have confirmed costs/suitability and are evaluated under the SAME protected profile. A linked product_ref reuses that goal in preview rather than duplicating commitments; using its protected money for a purchase needs separate funding reconciliation, not automatic withdrawal.

For a purchase of the linked goal, a read-only what-if may set `use_linked_goal_savings:true` and `goal_savings_in_current_cash:true` only after the user confirms that saved funds are included in current cash and can be used for this purchase. Supply confirmed reserve `coverage` and `budget.cash_excluded_goal_savings` as applicable. The simulation releases only the linked plan and its covered reserve once; it never changes the goal or moves money. If savings are outside the reported cash or the cash boundary is unknown, reconcile first and do not infer a buy verdict.

Default target date = locally computed end of current Bangkok month. Change-date reruns pure functions, no search or write. UI date_reports contains precomputed results through month-end, or at most 93 days when complete forecast supports that horizon; changing to one of these dates switches results without follow-up/LLM. Beyond it, or when fresh inputs required, host follow-up is the honest fallback. Calculations are never done by JavaScript. Suggested date is today when current finances allow; otherwise the requested date only if full portfolio forecast makes that plan feasible. No promised future income or guessed ETA from monthly surplus with competing goals.

New-plan preview may use virtual zero ONLY as an explicitly labeled UNSAVED scenario. This is not a claim about real already-saved money. Creating a goal requires confirmed name, target, date and user consent; unknown savings remain null and incomplete finances or infeasibility do not block creation. Do not allocate funds automatically or divert emergency or other goals.

## Start a goal, not a purchase

start_goal renders a concrete proposal; no write. If saved amount changes, recalculate/review. The review_token binds product, goal, profile, budget, forecast, coverage, current date and store revision. Confirm_goal requires --consent, matching review_token, expected_revision and operation_id, but not a confirmed free-cash source or complete finances. Stale inputs invalidate approval and require a refreshed review. Actual allocation requires separate strict validation and consent.

On confirmed plan, existing GoalStore creates+activates in one consented transaction via activate_on_create=true even when feasibility is unknown or not feasible; no funds are allocated. Show a calendar only when the required data exists. Goal entries remain virtual tracking; never write database.csv, transfer money or place orders. Existing linked goals must be updated through goal management, not duplicated. Repeated confirmation cannot create a second linked goal. General GoalStore revision/idempotency/duplicate-day protections still apply.

## UI and low usage

Components are shared entry, product confirmation, purchase goal card; savings progress/calendar reuse existing goal components after activation. Do not generate source each response. Render only fields used in UI, not full forecast/profile. Small UI choices remain local. No real financial data goes to search/image services or MCP POC servers. Native question/selection is fallback when inline unavailable; show product options and actions in the same workflow. Personality is short, caring and subordinate to engine results.

Actual browser/host click validation of this new component is distinct from Node DOM-stub tests; never claim all buttons/merchant images work in Codex until observed. Welcome click-to-follow-up was previously observed working. No usage percentage claim without measurement.
