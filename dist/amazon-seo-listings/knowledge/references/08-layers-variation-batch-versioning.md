# Layers, regeneration, variations, batch, versioning, audit

> Source: original agent specification, sections preserved verbatim. Where this file conflicts with `SKILL.md` section "Precedence and errata", `SKILL.md` wins.

## 54. Feed vs Copy Separation

Always maintain four layers:

## Content / SEO

- Title
- Item Highlights
- Bullet Points
- Description
- Backend Search Terms

## Catalog

- Brand
- Manufacturer
- GTIN
- Product Type
- Material
- Dimensions
- Compatibility
- Country of Origin
- Product attributes

## Offer / Pricing

- Sale Price
- Standard Price
- List Price
- MAP
- Min Price
- Max Price
- Business Price
- Quantity Tiers

## Compliance

- Warnings
- Claims
- Certifications
- Country of Origin
- Regulatory data

## 55. Regeneration Policy

Do not regenerate unaffected data.

If only price changes:

- Update Pricing Layer only.
- Do not rewrite SEO/content.

If SEO changes:

- Update SEO/content.
- Do not change verified TTX or pricing.

If TTX changes:

- Revalidate affected attributes, claims, content, compatibility and category.

If marketplace changes:

- Regenerate localization, local SEO, content, units and currency validation.
- Keep global product facts unchanged.

If only one SKU changes:

- Process only that SKU and its dependencies.

## 56. Global vs Marketplace Data

Maintain:

## Global Product Data

- SKU
- GTIN
- Model
- Manufacturer
- TTX
- Dimensions
- Material
- Compatibility
- Evidence

## Marketplace Data

- Marketplace
- Language
- SEO
- Title
- Bullets
- Description
- Backend
- Price
- Currency
- Category mapping
- Validation

One product may have separate records for:

- DE
- FR
- IT
- ES
- US
- Other marketplaces

without duplicating global factual data.

## 57. Variation Logic — Phase 2

Variation creation occurs only after base products are normalized and loaded.

Workflow:

`Parent Candidate Detection → Variation Theme Detection → Child Validation → Parent Logic → Relationship Generation`

Potential variation dimensions:

- Color
- Size
- Flavor
- Scent
- Model
- Capacity
- Pack Size
- Pattern
- Configuration

Do not create variations during initial product ingestion unless explicitly instructed.

## 58. Variation Validation

Check:

- Same product family
- Same core product
- Valid category variation theme
- Correct child attributes
- Unique child identifiers
- No unrelated products grouped together

Possible statuses:

- `VARIATION_READY`
- `VARIATION_REVIEW_REQUIRED`
- `VARIATION_INVALID`

## 59. Parent / Child Inheritance

Potentially inheritable:

- Brand
- Product family
- Core product identity

Do not blindly inherit:

- GTIN
- Color
- Size
- Dimensions
- Weight
- Pack quantity
- Price
- Compatibility
- Backend terms
- Exact claims

## 60. Batch Processing

Agent 1 must support:

- 1 SKU
- 50 SKUs
- 1,000 SKUs
- 10,000+ SKUs

Do not assume manual review of every SKU is possible.

## 61. Batch Summary

Return:

- Total SKUs
- Ready
- Ready with Warnings
- Needs Review
- Data Required
- Blocked
- Policy Risk
- Price Conflict
- Identifier Conflict

Also return a separate issue list.

## 62. Incremental Processing

Do not reprocess unchanged records.

Use:

- Hashes
- Version IDs
- Timestamps
- Source fingerprints

If 37 out of 5,000 SKUs changed, process only those 37 unless shared dependencies require more.

## 63. Versioning

Track:

- `listing_version`
- `seo_source_date`
- `seo_version`
- `pricing_policy_version`
- `amazon_policy_version`
- `product_data_version`
- `catalog_source_version`
- `evidence_version`
- `export_version`
- `content_hash`
- `source_hash`

## 64. Audit Trail

Every normalized/generated field should store:

- Value
- Source
- Source Version
- Confidence
- Status
- Last Updated

Possible source types:

- `USER_INPUT`
- `TTX`
- `PACKAGING_IMAGE`
- `CATALOG`
- `MANUFACTURER_DATA`
- `AMAZON_EXISTING`
- `SEO`
- `CALCULATED`
- `INFERRED`

High-risk inferred values must not be published without approval.
