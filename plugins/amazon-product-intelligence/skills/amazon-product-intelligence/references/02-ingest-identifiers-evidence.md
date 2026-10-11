# Ingest, identifiers, evidence matrix, image-to-SKU matching

> Source: original agent specification, sections preserved verbatim. Where this file conflicts with `SKILL.md` section "Precedence and errata", `SKILL.md` wins.

## 6. Stage 1 — Ingest & Normalize

Normalize all incoming data before generating content.

Create one normalized product record per SKU.

Normalize:

- identifiers
- brand
- product name
- model
- manufacturer
- size
- count
- pack quantity
- dimensions
- weight
- material
- color
- compatibility
- technical specifications
- ingredients
- claims
- certifications
- warnings
- country of origin
- marketplace
- pricing

Never silently alter user-supplied factual values.

## 7. Identifier Strategy

Supported identifier modes:

- EAN
- UPC
- GTIN
- ASIN
- SKU
- GTIN exemption

Possible statuses:

- `GTIN_VALID`
- `GTIN_EXEMPT`
- `GTIN_MISSING`
- `GTIN_INVALID`
- `IDENTIFIER_CONFLICT`
- `IDENTIFIER_DUPLICATE`
- `ASIN_MATCH_FOUND`
- `NEW_PRODUCT_CANDIDATE`

Rules:

- Do not generate fake EAN / UPC / GTIN.
- Do not infer GTIN exemption.
- If `GTIN_EXEMPT = true`, do not require or fabricate GTIN.
- Store GTIN exemption as a separate explicit status.
- Do not identify a product solely by name.
- Do not silently replace one identifier with another.

## 8. Identifier Validation

Check for:

- Duplicate EAN across unrelated SKUs
- Duplicate UPC across unrelated SKUs
- Same SKU with conflicting identifiers
- One identifier linked to multiple incompatible products
- Pack vs single-unit conflicts
- Parent/child confusion
- Existing ASIN mismatch

If conflict exists:

`IDENTIFIER_CONFLICT`

User review is required.

## 9. Input Validation

Before content generation validate:

- Marketplace exists
- Currency is compatible with marketplace
- Identifier state is known
- Product Type can be resolved
- Pricing fields are valid
- Units are valid
- TTX does not internally contradict itself
- Pack size is coherent
- Model is coherent
- Compatibility is coherent

Possible statuses:

- `PASS`
- `WARNING`
- `CONFLICT`
- `DATA_REQUIRED`
- `BLOCKED`

## 10. Stage 2 — Product Evidence Matrix

Build a Product Evidence Matrix for every SKU.

Recommended structure:

| SKU | Identifier | Attribute / Claim | Value | Source | Evidence Location | Confidence | Status |
|---|---|---|---|---|---|---|---|

Example:

| A001 | 4000000000001 | IP Rating | IPX4 | Packaging Image | image_03_front | HIGH | VERIFIED |

The Product Evidence Matrix must be built before writing claims.

## 11. Image / Catalog Evidence Extraction

If the user supplies catalogs or product images, extract factual data such as:

- SKU
- EAN
- UPC
- Model
- Color
- Material
- Dimensions
- Ingredients
- Compatibility
- Certifications
- Technical markings
- Warnings
- Product claims
- Country-of-origin markings
- Package quantity
- Included accessories

Never assume a claim visible on one SKU applies to neighboring SKUs.

## 12. Image-to-SKU Matching

Every image/catalog page must be associated with the correct product.

Match using:

- SKU
- EAN
- UPC
- Model
- Product name
- Color
- Pack size
- Catalog position
- Label data

Possible statuses:

- `IMAGE_SKU_MATCH_HIGH`
- `IMAGE_SKU_MATCH_MEDIUM`
- `IMAGE_SKU_MATCH_LOW`
- `IMAGE_SKU_MATCH_CONFLICT`

If confidence is low, do not automatically use extracted claims or attributes.
