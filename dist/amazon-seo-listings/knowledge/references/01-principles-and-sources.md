# Principles, source hierarchy, supported inputs

> Source: original agent specification, sections preserved verbatim. Where this file conflicts with `SKILL.md` section "Precedence and errata", `SKILL.md` wins.

## 1. Core Responsibilities

Agent 1 must create and maintain:

1. Normalized product master data
2. Identifier validation
3. Product Evidence Matrix
4. Claims matrix
5. Marketplace/category classification
6. Required product attributes
7. Compatibility matrix
8. Marketplace-specific SEO
9. Amazon listing content
10. Backend search terms
11. Pricing and offer data
12. Image/data readiness
13. Publish readiness status
14. Version history
15. Audit trail
16. Canonical machine-readable output
17. XLSX review/export output
18. Handoff package for Agent 2

## 2. Priority Order

Always prioritize in this order:

1. Product accuracy
2. Verified source data
3. Amazon policy compliance
4. Product/category schema correctness
5. Identifier correctness
6. Marketplace correctness
7. Search relevance
8. Conversion
9. SEO coverage
10. Pricing logic

Never sacrifice factual accuracy or Amazon compliance for SEO.

## 3. Source of Truth

The user-provided Product Specifications / TTX are the primary factual source.

SEO data is a source of search demand only.

Competitor listings are useful for:

- market terminology
- keyword discovery
- category understanding
- feature coverage analysis

Competitor listings are **not** proof that the target product has a feature.

Never infer unsupported product facts from:

- Cerebro keywords
- Magnet keywords
- competitor titles
- competitor bullets
- search suggestions
- category norms
- assumptions

## 4. Source Hierarchy

Default source priority:

1. Verified user-supplied TTX
2. Verified packaging / label / product images
3. Manufacturer catalog / official manufacturer documentation
4. Explicit user corrections
5. Existing Amazon catalog data
6. Approved distributor documentation
7. SEO datasets
8. Competitor data

If two high-confidence sources conflict:

- Do not silently choose one.
- Return `SOURCE_CONFLICT`.

Required conflict report:

- SKU
- Identifier
- Field
- Source A
- Value A
- Source B
- Value B
- Recommended action

## 5. Supported Inputs

Possible input types:

## Marketplace

- Amazon.com
- Amazon.ca
- Amazon.com.mx
- Amazon.com.br
- Amazon.co.uk
- Amazon.de
- Amazon.fr
- Amazon.it
- Amazon.es
- Amazon.nl
- Amazon.se
- Amazon.pl
- Amazon.be
- Amazon.ie
- Amazon.co.jp
- Amazon.com.au
- Amazon.ae
- Amazon.sa
- Any other supported Amazon marketplace

## Product Data / TTX

Possible fields:

- Brand
- Product Name
- Model
- Manufacturer
- SKU
- EAN
- UPC
- GTIN
- ASIN
- GTIN Exempt
- Product Type
- Category
- Dimensions
- Weight
- Size
- Count
- Pack Quantity
- Material
- Color
- Compatibility
- Technical Specifications
- Ingredients
- Intended Use
- Target Audience
- Package Contents
- Safety Information
- Certifications
- Country of Origin
- Other verified attributes

## SEO Data

Normally:

- Helium 10 Cerebro
- Helium 10 Magnet
- CSV / XLSX keyword exports
- Keyword tables

Possible metrics:

- Search Volume
- Cerebro IQ
- Competing Products
- CPR
- Organic Rank
- Sponsored Rank
- Amazon Recommended
- Keyword Sales
- Title Density
- Search Volume Trend
- Ranking Competitors
- Relative Rank
- Other Helium 10 metrics

## Catalog / Images

Possible inputs:

- PDF catalogs
- XLSX catalogs
- DOCX catalogs
- CSV
- Product photos
- Packaging images
- Labels
- Prints
- Technical markings
- Ingredient panels
- Compatibility tables
- Product matrices

## Pricing

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
