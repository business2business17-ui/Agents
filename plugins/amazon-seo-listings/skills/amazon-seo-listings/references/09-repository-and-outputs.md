# Diff engine, repository workflow, canonical JSON and XLSX outputs

> Source: original agent specification, sections preserved verbatim. Where this file conflicts with `SKILL.md` section "Precedence and errata", `SKILL.md` wins.

## 65. Diff Engine

When an earlier version exists, generate field-level differences.

Example:

## Title

OLD → NEW

Reason: Updated DE SEO

## Bullet 3

OLD → NEW

Reason: New verified compatibility data

## Sale Price

24.99 → 22.99

Reason: User input

## Description

UNCHANGED

## 66. GitHub / Repository Workflow

Recommended repository structure:

```text
/products/raw/
/products/normalized/
/products/evidence/
/catalogs/
/images/
/seo/
/pricing-policies/
/marketplaces/
/schemas/
/output/json/
/output/jsonl/
/output/xlsx/
/output/issues/
/versions/
```

Possible files:

```text
SKU123_global.json
SKU123_DE.json
SKU123_US.json
```

## 67. Repository Rules

Never overwrite original raw source files.

Generated data belongs in:

- normalized
- output
- versions

Preserve:

- Source history
- Change history
- Version references
- Hashes
- Generation date

## 68. Canonical Machine Output

Primary machine-readable output:

- JSON
- JSONL for batch processing

Recommended record structure:

```json
{
  "internal_product_id": "",
  "sku": "",
  "identifiers": {
    "ean": null,
    "upc": null,
    "gtin": null,
    "asin": null,
    "gtin_exempt": false,
    "identifier_mode": "",
    "status": ""
  },
  "global_product_data": {},
  "evidence": {},
  "claims": {},
  "compatibility": {},
  "marketplaces": {},
  "version": {},
  "audit": {},
  "publish_status": ""
}
```

## 69. XLSX Export

XLSX is the human-review and operational export format.

Recommended sheets:

1. Products
2. Content
3. Pricing
4. SEO
5. Attributes
6. Compatibility
7. Claims
8. Warnings
9. Images
10. Versions
11. Audit
12. Handoff

## 70. Products Sheet

Recommended columns:

- Internal Product ID
- SKU
- EAN
- UPC
- GTIN
- GTIN Exempt
- ASIN
- Brand
- Product Name
- Model
- Product Type
- Marketplace
- Country of Origin
- Publish Status

## 71. Content Sheet

Recommended columns:

- SKU
- Marketplace
- Language
- Title
- Item Highlights
- Bullet 1
- Bullet 2
- Bullet 3
- Bullet 4
- Bullet 5
- Description
- Backend Search Terms
- Backend Bytes

## 72. Pricing Sheet

Recommended columns:

- SKU
- Marketplace
- Currency
- Sale Price
- Standard Price
- List Price
- MAP
- Min Seller Allowed Price
- Max Seller Allowed Price
- Business Price
- Quantity Tier 1
- Quantity Tier 2
- Quantity Tier 3
- Quantity Tier 4
- Pricing Policy Version

## 73. SEO Sheet

Recommended columns:

- SKU
- Marketplace
- Keyword
- Search Volume
- Tier
- Placement
- Status
- Reason
- SEO Source Date

## 74. Attributes Sheet

Recommended columns:

- SKU
- Attribute
- Value
- Source
- Confidence
- Required
- Status

## 75. Compatibility Sheet

Recommended columns:

- SKU
- Compatible Brand
- Compatible Model
- Generation
- Year
- Device
- Not Compatible With
- Source
- Confidence

## 76. Claims Sheet

Recommended columns:

- SKU
- Claim
- Source
- Evidence
- Claim Type
- Risk
- Status
- Action

## 77. Warnings Sheet

Recommended columns:

- SKU
- Issue Type
- Severity
- Field
- Issue
- Recommended Action

## 78. Images Sheet

Recommended columns:

- SKU
- Image
- Image Type
- Matched Product
- Match Confidence
- Evidence Extracted
- Required / Optional
- Status

## 79. Versions Sheet

Recommended columns:

- SKU
- Marketplace
- Listing Version
- SEO Version
- Product Data Version
- Pricing Policy Version
- Amazon Policy Version
- Source Hash
- Content Hash
- Last Updated
