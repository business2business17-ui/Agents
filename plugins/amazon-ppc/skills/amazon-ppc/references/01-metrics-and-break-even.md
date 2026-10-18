# 01 - Metrics, break-even, objectives

Definitions (use the same ones in every output; state the attribution window of the source, usually 7 or 14 days):

| Metric | Formula | Notes |
|---|---|---|
| CTR | clicks / impressions | |
| CPC | spend / clicks | |
| CVR | orders / clicks | click-to-order |
| ACOS | spend / ad sales | ad-attributed sales only |
| ROAS | ad sales / spend | = 1 / ACOS |
| TACOS | spend / total sales (organic + ad) | needs the Business Report for the same dates; never estimate it from an ads report alone |
| CPA | spend / orders | |
| RPC | ad sales / clicks | revenue per click; bid ceiling driver |

Zero denominators: print `N/A` and the reason, never 0 or infinity.

## Break-even and target

- **Break-even ACOS** = profit per unit before ads / net selling price (the ACOS at which ads eat all profit). Profit before ads = price - product cost - referral fee - FBA/MFN fee - returns reserve - other variable costs (`scripts/margin_calc.py`, `scripts/performance_calc.py`).
- **Target ACOS** = break-even ACOS - desired profit margin after ads.
- **Max CPC** = selling price x target ACOS x CVR. If Amazon's suggested bid is above Max CPC, say so: accept a loss for ranking, raise price / CVR, or skip the keyword.
- **Profit after ads** = sales - product cost - Amazon fees - fulfillment - discounts - returns - ad spend. With ads-attributed sales only it is an ad-level view, not store profit.
- VAT: ACOS must use the same sales basis (gross or net of VAT) as the report; `performance_calc.py` detects or asks (`--sales-basis`).

## Campaign objective (decides what "good" means)

| Objective | Typical target | Success signal |
|---|---|---|
| Discovery (auto / broad / category) | ACOS above break-even is tolerated for a short, capped time | new converting search terms, impressions share |
| Control (exact, proven terms) | at or below target ACOS | stable ACOS, controlled spend |
| Growth | around break-even | sales and rank growth at acceptable TACOS |
| Profit | below target ACOS | margin after ads |
| Defense (brand, own ASIN) | low ACOS, high share | brand terms held |
| Launch / rank | above break-even for 4-8 weeks, capped | rank, reviews, velocity |

Do not infer the objective from match type, name or ACOS alone: ask once (recommend from the data) or mark it `Unknown` and stay conservative.

## Sufficiency (defaults, change with `--min-clicks` etc.)

- Bid change: at least 20 clicks on the target (or 10 clicks with zero orders for a cut).
- Negative: at least 10-15 clicks and zero orders and spend above 1.5 x target CPA; never from one day; never brand / own ASIN.
- Harvest: at least 2 orders and ACOS at or below target on the search term.
- Under the minimum: `Watch` and re-check in 7 days.
