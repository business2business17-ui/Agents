# 02 - Which companion skill for which task

The companion skills are installed next to `amazon-ppc` in `skills/`. They give methods and report layouts; `SKILL.md` of `amazon-ppc` (facts, evidence, no fabrication, approval before writes) wins on conflict. Their numbers (benchmarks, thresholds) are defaults to be checked against the user's data.

| Task | Load |
|---|---|
| New product / new campaigns, blueprint, starting bids, negative seed list | `amazon-ppc-campaign` |
| Whole-account optimization, weekly review, user does not know where to start | `amazon-ads-optimizer` (+ `playbooks/weekly-review.md`) |
| Account takeover / full audit | `amazon-ads-audit` |
| Status scan, watchlist | `campaign-health-monitor` |
| Sudden metric movement | `anomaly-detection` |
| Sustained decline: what dropped and why | `performance-drop-diagnosis`, `amazon-ads-performance-drop-diagnosis` |
| Search terms: promote / negate / route | `search-term-analysis`, `amazon-search-term-harvest-planner` |
| Keywords | `keyword-optimization` |
| Negatives / targeting exclusions | `negative-targeting` |
| Bids | `bid-optimization` |
| Budgets | `budget-optimization` |
| Placements (top of search, product pages, rest) | `placement-optimization` |
| Profit / margin view of ads | `profitability-analysis` |
| Where to grow | `growth-opportunity-finder`, `amazon-growth-opportunity-finder`, `amazon-account-growth-operating-system` |
| Test plan | `experiment-planner` |
| Did the last change work | `post-change-review` |
| Live account through Marketplace Ad Pros MCP | `amazon-ads` |
| Live account through Rocketcart MCP | `rocketcart-amazon-ads-live-review` |

Listing quality, keywords for the listing and A+ are not PPC: hand over to `amazon-seo-listings`. Feed files: `amazon-feeds`. Creatives for Sponsored Brands / Display: `amazon-creative-studio`.
