# 03 - Search terms: harvest, negatives, funnel

Source: search term report (Seller Central / Amazon Ads console, Sponsored Products; also SB). `scripts/ppc_search_terms.py` reads CSV and XLSX from any marketplace (header and currency variants are normalized) and returns four views.

## Keyword funnel

```
Auto (discover)  -> terms with 2+ orders -> Manual Broad / Phrase (test) -> terms with 2+ orders at target ACOS -> Manual Exact (scale)
```
When a term is promoted, add it as **negative exact** in the source campaign so it does not compete with itself. Exact campaigns need no negatives; Auto, Broad and Product Targeting get the Exact keywords as negatives.

## Harvest to exact (promote)

Candidate: search term with orders >= `--min-orders` (default 2) and ACOS <= target on enough clicks, not already an exact keyword in the account. Start bid = min(avg CPC x 1.1, Max CPC at target ACOS); never above Max CPC without telling the user. Route by evidence: strong -> Exact; promising but thin -> Broad / Phrase test; competitor ASIN converts -> product targeting. Keep a watchlist for 1 order.

## Negatives

Candidate: clicks >= `--neg-clicks` (default 12) and orders = 0 and spend >= 1.5 x target CPA (or a fixed floor). Choose the type:
- **Negative exact** for a specific wasteful query or a term just promoted.
- **Negative phrase** for a wasteful modifier (free, cheap, used, DIY, how to, review, reddit) or a wrong product / material / intent shared by several queries.
Never negate: own brand, own ASINs, launch / rank-defense terms, terms with orders in another period without checking. Review phrases before applying: phrase negatives can cut good traffic.

## Seed negatives (new campaigns)

1. Exact keywords as negative exact in Auto / Broad / Product Targeting.
2. Irrelevant intent: wrong material, wrong product type, wrong use ("how to clean", "DIY").
3. Generic waste modifiers per language of the marketplace.
4. Own ASIN as negative product target in the ASIN-targeting campaign.

## Reading the output

`ppc_search_terms.py` sheets: **Campaign Summary** (spend, sales, ACOS, ROAS, CTR, CVR, CPC), **Bid Recommendations** (per target: action, suggested bid, reason), **Negative Keywords**, **Keyword Harvest**, **Watch** (insufficient data). Every row carries the evidence (clicks, orders, spend, ACOS) so the user can reject it. Rows are suggestions; see `06-safety-and-mutation.md`.
