# Processing Report round-trip, error taxonomy, catalog conflicts, ownership, partial update safety

> Source: original agent specification, sections preserved verbatim. Where this file conflicts with `SKILL.md` section "Precedence and errata", `SKILL.md` wins.

## 49. Processing Report Round-Trip — Mandatory

Processing Report handling is a core Agent 2 responsibility, not an optional future feature.

After Amazon upload, Agent 2 must be able to ingest the Processing Report and map every error/warning back to:

Amazon Error / Warning
→ SKU
→ Amazon Row
→ Amazon Field
→ Feed Cell
→ Agent 1 Source Path
→ Source Value
→ Submitted Value
→ Error Reason
→ Suggested Fix
→ Correction Safety Level

Possible upload result states:

- `ACCEPTED`
- `ACCEPTED_WITH_WARNINGS`
- `PARTIALLY_ACCEPTED`
- `REJECTED`
- `PROCESSING_UNKNOWN`

Possible row-level states:

- `ROW_ACCEPTED`
- `ROW_ACCEPTED_WITH_WARNING`
- `ROW_REJECTED`
- `ROW_NOT_PROCESSED`

Agent 2 must preserve the exact Processing Report source and associate it with:

- batch_id
- feed filename
- template fingerprint
- submission version
- submission timestamp
- Agent 1 record version
- Agent 2 feed version

## 50. Amazon Error Taxonomy

Classify Amazon errors/warnings into categories such as:

- `IDENTIFIER_ERROR`
- `GTIN_ERROR`
- `GTIN_EXEMPTION_ERROR`
- `ENUM_ERROR`
- `REQUIRED_FIELD_ERROR`
- `DATA_TYPE_ERROR`
- `LENGTH_ERROR`
- `UNIT_ERROR`
- `CATEGORY_ERROR`
- `PRODUCT_TYPE_ERROR`
- `CATALOG_CONFLICT`
- `ATTRIBUTE_CONFLICT`
- `BRAND_CONFLICT`
- `MODEL_CONFLICT`
- `TITLE_CONFLICT`
- `PRICE_ERROR`
- `SALE_PRICE_ERROR`
- `CURRENCY_ERROR`
- `VARIATION_ERROR`
- `PARENT_CHILD_ERROR`
- `IMAGE_ERROR`
- `COMPLIANCE_ERROR`
- `DANGEROUS_GOODS_ERROR`
- `SCHEMA_ERROR`
- `TEMPLATE_ERROR`
- `UNKNOWN_AMAZON_ERROR`

Every error should receive:

- severity
- affected SKU(s)
- affected field(s)
- whether safe auto-fix is possible
- whether user review is required
- whether Agent 1 correction is required

## 51. Catalog Conflict Handling

If Amazon returns an existing-catalog conflict involving fields such as:

- Brand
- Product Name
- Model
- Manufacturer
- GTIN
- Size
- Pack Quantity
- Color
- Variation
- Product Type

Agent 2 must NOT automatically overwrite Agent 1 data to match Amazon.

Return:

`CATALOG_CONFLICT`

Include:

- SKU
- ASIN if known
- Amazon current value
- Agent 1 value
- submitted value
- conflict field
- error code/message
- recommended review path

If resolving the conflict would materially change product identity:

`AGENT1_DATA_REVIEW_REQUIRED`

## 52. Contribution Ownership Awareness

Where Amazon already controls or strongly owns a catalog attribute, Agent 2 must distinguish:

- `SELLER_CONTRIBUTION_ALLOWED`
- `SELLER_CONTRIBUTION_LIMITED`
- `AMAZON_CATALOG_AUTHORITY`
- `UNKNOWN_OWNERSHIP`

Agent 2 should not repeatedly resubmit fields that Amazon rejects as non-authoritative unless a correction workflow is explicitly chosen.

## 53. Partial Update Safety

For update workflows, Agent 2 must explicitly determine the meaning of omitted or blank fields.

Never assume:

blank = no change

or:

blank = clear value

unless confirmed by the current template/action semantics.

Maintain field actions where relevant:

- `SET`
- `NO_CHANGE`
- `CLEAR`
- `OMIT`
- `NOT_APPLICABLE`

For partial updates, populate only fields intended for change plus any fields required by the template.
