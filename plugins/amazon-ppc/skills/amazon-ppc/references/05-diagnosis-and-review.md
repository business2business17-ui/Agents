# 05 - Diagnosis, weekly review, post-change review

## Performance drop (order of checks)

1. **Data first**: same dates, same attribution window, data lag (2-3 days), currency, marketplace, partial period.
2. **Demand / market**: seasonality, events, category trend.
3. **Product side**: stock-outs, Buy Box, price change, rating / review drop, listing changes (hand over to `amazon-seo-listings` if the listing is the cause).
4. **Account side**: budget limits, bid / strategy changes, new negatives, paused campaigns, structure changes - use the change history.
5. **Traffic quality**: impressions vs clicks vs CVR: where does the funnel break.
6. **Competition**: CPC inflation, lost impression share.
Output: ranked causes with evidence and confidence, what is not known, the next data to pull. No single-cause claims on one metric.

## Weekly review (Monday)

This week vs prior week (and vs same week last year if events matter): spend, sales, ACOS, TACOS (from Business Report), top and bottom campaigns, budget-limited campaigns, new converting terms (harvest), wasted spend (negatives), pending re-checks. Output: scorecard + at most 10 actions with owner and date.

## Post-change review

Re-check at 3 / 7 / 14 days on the same window length. Mark each change `Worked / No effect / Hurt / Too early`; control for seasonality and other changes made in the same period; carry the result into project memory so the same mistake is not repeated.

## Experiments

One variable at a time, a stated hypothesis, a metric, a minimum sample, an end date (`experiment-planner`).
