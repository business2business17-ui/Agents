# Pricing engine (see also shared-pricing-and-updates.md)

> Source: original agent specification, sections preserved verbatim. Where this file conflicts with `SKILL.md` section "Precedence and errata", `SKILL.md` wins.

## 38. Stage 6 — Pricing Engine

Supported modes:

- `DIRECT`
- `DERIVED`
- `PARTIAL`

The normal workflow may use:

`PRICE_INPUT_DEFAULT = sale_price`

If the user gives only one price and the configured workflow says Sale Price is default:

Treat it as:

`sale_price = supplied value`

Do not reinterpret as `standard_price`.

## 39. Pricing Fields

Possible fields:

- `standard_price`
- `currency`
- `list_price`
- `map_price`
- `sale_price`
- `sale_start_date`
- `sale_end_date`
- `minimum_seller_allowed_price`
- `maximum_seller_allowed_price`
- `business_price`
- `quantity_price_type`
- `quantity_lower_bound_1`
- `quantity_price_1`
- `quantity_lower_bound_2`
- `quantity_price_2`
- `quantity_lower_bound_3`
- `quantity_price_3`
- `quantity_lower_bound_4`
- `quantity_price_4`

## 40. Derived Pricing

If only Sale Price is provided:

1. Preserve Sale Price exactly.
2. Calculate other price fields only from configured Pricing Policy.
3. Never invent percentages.

Supported rule types:

- Percentage markup
- Percentage discount
- Reverse discount
- Fixed amount
- Margin-based formula
- Custom formula

## 41. Reverse Discount Math

If:

`Sale Price = Standard Price × 0.90`

then:

`Standard Price = Sale Price / 0.90`

Not:

`Sale Price × 1.10`

Always distinguish markup from reverse discount math.

## 42. Pricing Policy Version

Every derived calculation must reference:

`pricing_policy_version`

Store:

- Source field
- Formula
- Raw result
- Rounded result
- Policy version

## 43. Price Rounding

Supported examples:

- `2_DECIMALS`
- `END_99`
- `END_95`
- `END_90`
- `INTEGER`
- `CUSTOM`

Never apply psychological rounding unless configured.

## 44. List Price

Do not fabricate MSRP.

If `list_price` is intended to represent genuine MSRP/reference price, it must have support.

Do not create artificial list prices solely to create a visible discount.

## 45. MAP Price

Never derive MAP unless explicitly configured.

MAP is not a generic marketing price.

## 46. Price Validation

Validate:

- Numeric price values
- Currency
- Sale dates
- Price guardrails
- Business pricing
- Quantity tiers
- User-supplied values vs calculated values

Possible statuses:

- `PRICE_VALID`
- `PRICE_CONFLICT`
- `PRICE_POLICY_CONFLICT`
- `CURRENCY_CONFLICT`
- `PRICE_DATA_REQUIRED`
