# 04 - Bids, budgets, placements

## Bids

Primary method (value based): suggested bid = RPC x target ACOS, where RPC = ad sales / clicks of that target; cap by Max CPC; floor by the marketplace minimum bid. `ppc_search_terms.py` applies it and shows the old and the new bid.

Rule-of-thumb cross-check (acts only on targets with 20+ clicks):

| Situation | Action |
|---|---|
| ACOS > 200% of target | cut 30-50% |
| ACOS 100-199% | cut 20% |
| above target by up to 99% | cut 10-15% |
| within +-10% of target | keep |
| below target and impression share / rank matters | raise 10-20% |
| 10+ clicks, 0 orders | cut hard or pause; check relevance first |

Limit one change step per target per review (no more than +-30% at once); wait 7 days for data before the next step. Bids on Dynamic "down only" campaigns behave differently: say which strategy the campaign uses.

Starting bids for new campaigns (no data): Exact = Amazon suggested bid or Max CPC, whichever is lower; Broad 70-80% of Exact; Auto 50-70%; Product Targeting 50-70%. Suggested bids come from Seller Central / MCP (`get_amazon_ads_ad_group_bid_recs`), never invented.

## Budgets

- Budget limited campaign (out-of-budget before the end of the day) with ACOS at or below target: raise, in steps; funded by cutting campaigns that stay above break-even with enough data.
- Campaign far below budget: the constraint is bids / targeting / relevance, not budget.
- Events (Prime Day, Q4): plan increases beforehand, compare with the same window last year, use budget rules; set a re-check date.
- Keep a floor budget for Defense campaigns.

## Placements

Compare Top of Search, Product Pages, Rest of Search on spend, clicks, orders, CVR, CPC, ACOS. Raise the placement multiplier only where ACOS is at or below target on enough clicks; do not stack a big multiplier on a high base bid; state the bidding strategy (down only / up and down / fixed) before judging.

## Cannibalization

Same term in several campaigns: find the winner by ACOS and share, negate in the others (exact), keep one owner per term per match type.
