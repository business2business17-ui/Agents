# Image readiness, validation, confidence, publish status, checkpoints

> Source: original agent specification, sections preserved verbatim. Where this file conflicts with `SKILL.md` section "Precedence and errata", `SKILL.md` wins.

## 47. Stage 7 — Image Data Readiness

Assess whether available images are enough.

Possible statuses:

- `IMAGE_SUFFICIENT`
- `IMAGE_INPUT_REQUIRED`
- `IMAGE_OPTIONAL`

If images are needed, ask specifically for:

- Front packaging
- Back label
- Ingredient panel
- Dimension image
- Certification marking
- Compatibility chart
- Included contents
- Model label
- Country-of-origin label

Do not request images when unnecessary.

## 48. Image Asset Recommendations

Where useful, provide suggested asset list:

- Main image
- Side image
- Dimensions
- Packaging
- Technical features
- Compatibility
- Ingredients / label
- Lifestyle
- Compliance markings
- Included accessories

## 49. Stage 8 — Validation & Publish Readiness

Classify issues as:

## Hard Errors

Examples:

- Invalid GTIN
- Identifier conflict
- Prohibited claim
- Required attribute missing
- Price conflict
- Wrong currency
- Invalid variation
- Unsupported regulated claim
- Impossible compatibility

## Soft Warnings

Examples:

- Old SEO data
- Optional image missing
- Weak keyword coverage
- Low category confidence
- Optional attribute missing
- Limited lifestyle assets

## 50. Confidence Score

Supported confidence values:

- `HIGH`
- `MEDIUM`
- `LOW`

Missing required data is not `LOW`.

It must be:

`DATA_REQUIRED`

Possible confidence dimensions:

- Category
- Image match
- Claim
- Compatibility
- Identifier
- Source

## 51. Publish Readiness Status

Every SKU/marketplace record must receive exactly one main status:

- `READY_TO_PUBLISH`
- `READY_WITH_WARNINGS`
- `NEEDS_REVIEW`
- `DATA_REQUIRED`
- `POLICY_RISK`
- `PRICE_CONFLICT`
- `BLOCKED`

## 52. No Silent Correction

Never silently overwrite:

- EAN
- UPC
- GTIN
- Model
- Country of Origin
- Compatibility
- Price
- Dimensions
- Package count

If a conflict exists, show it.

## 53. Human Approval Checkpoints

## Checkpoint 1 — Data

Validate:

- TTX
- Identifiers
- Catalog evidence
- Claims
- Model
- Package configuration

## Checkpoint 2 — Content

Validate:

- SEO
- Listing
- Claims
- Localization

## Checkpoint 3 — Publish

Validate:

- Pricing
- Feed-required fields
- Marketplace
- Currency
- Identifiers
- Product Type

Batch processing may proceed automatically if no hard errors exist.
