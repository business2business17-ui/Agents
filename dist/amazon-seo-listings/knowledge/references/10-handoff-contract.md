# Agent 1 to Agent 2 handoff contract

> Source: original agent specification, sections preserved verbatim. Where this file conflicts with `SKILL.md` section "Precedence and errata", `SKILL.md` wins.

## 80. Agent 1 → Agent 2 Handoff Contract

Agent 1 does not directly publish to Amazon.

Agent 1 produces a canonical, validated, marketplace-specific product package.

Agent 2 will later transform this package into the exact Amazon:

- Product Type Definition
- Listings API structure
- Feed schema
- Feed payload
- Submission workflow

Agent 1 should not depend on a specific nested Amazon API path unless explicitly requested.

## 81. Handoff Schema Version

Every export must contain:

`handoff_schema_version`

Example:

`1.0.0`

Agent 2 should reject unsupported schema versions.

## 82. Required Handoff Record Identity

Every marketplace-specific record must include:

- `internal_product_id`
- `sku`
- `marketplace`
- `batch_id`
- `record_version`

Where applicable:

- EAN
- UPC
- GTIN
- ASIN

`internal_product_id` must remain stable across revisions.

## 83. Identifier Mode

Allowed values:

- `GTIN`
- `GTIN_EXEMPT`
- `MATCH_EXISTING_ASIN`
- `UPDATE_EXISTING_ASIN`

Agent 2 must not infer another identifier mode.

## 84. Operation Intent

Each record must specify one of:

- `CREATE`
- `UPDATE`
- `PARTIAL_UPDATE`
- `CONTENT_ONLY`
- `PRICE_ONLY`
- `OFFER_ONLY`

Future optional operations:

- `CLOSE_OFFER`
- `DELETE`

Agent 2 must respect operation intent.

## 85. Publish Status Rules for Agent 2

Allowed statuses:

- `READY_TO_PUBLISH`
- `READY_WITH_WARNINGS`
- `NEEDS_REVIEW`
- `DATA_REQUIRED`
- `POLICY_RISK`
- `PRICE_CONFLICT`
- `BLOCKED`

Agent 2 may automatically publish:

`READY_TO_PUBLISH`

`READY_WITH_WARNINGS` may be publishable only if configured workflow permits it.

Never automatically publish:

- `NEEDS_REVIEW`
- `DATA_REQUIRED`
- `POLICY_RISK`
- `PRICE_CONFLICT`
- `BLOCKED`

## 86. Field-Level Status

Critical fields should support:

- `value`
- `status`
- `source`
- `confidence`
- `last_updated`

Possible status values:

- `VALID`
- `WARNING`
- `DATA_REQUIRED`
- `CONFLICT`
- `BLOCKED`

## 87. Null Semantics

Use strict semantics:

- `null` = value unavailable
- `N/A` = field does not apply
- `DATA_REQUIRED` = field is required but missing

Do not use empty string interchangeably with null.

## 88. Data Types

Use deterministic machine-readable types.

Examples:

- Price → Decimal
- Quantity → Integer
- Boolean → `true` / `false`
- Date → ISO-8601
- Currency → ISO currency code
- Country → defined country-code format
- Text → UTF-8 string

Bad:

`"€19,99"`

Good:

```json
{
  "value": 19.99,
  "currency": "EUR"
}
```

## 89. Marketplace Isolation in Handoff

One SKU may have multiple marketplace records.

Example:

- SKU123 / DE
- SKU123 / FR
- SKU123 / US

Each marketplace record must have its own:

- Language
- SEO
- Content
- Currency
- Pricing
- Category mapping
- Validation
- Publish status

Global product facts remain shared.

## 90. Product Type Lock

After Product Type is validated:

`product_type_status = LOCKED`

Agent 2 must not independently change Product Type.

If Amazon rejects the Product Type, Agent 2 should return:

`AGENT1_DATA_REVIEW_REQUIRED`

## 91. Field Ownership

## Agent 1 owns

- Product facts
- Claims
- SEO
- Content
- Compatibility
- Catalog attributes
- Pricing logic
- Country of Origin
- Source validation
- Product Type selection
- Publish readiness

## Agent 2 owns

- Amazon PTD resolution
- Exact feed-field mapping
- API/feed payload creation
- Amazon enumeration mapping
- Submission validation
- Feed submission

Agent 2 may transform format.

Agent 2 must not silently change product meaning.

## 92. Changed Fields

Every update record should include:

`changed_fields`

Example:

```json
[
  "title",
  "backend_search_terms",
  "sale_price"
]
```

Agent 2 should update only changed fields when partial updates are allowed.

## 93. Unresolved Required Fields

Include:

`unresolved_required_fields`

Example:

```json
[
  "country_of_origin"
]
```

If mandatory unresolved fields remain, the record must not be `READY_TO_PUBLISH`.

## 94. Hard Blockers

Include:

`hard_blockers`

Examples:

- `INVALID_GTIN`
- `IDENTIFIER_CONFLICT`
- `REQUIRED_ATTRIBUTE_MISSING`
- `PROHIBITED_CLAIM`
- `PRICE_CONFLICT`
- `CURRENCY_CONFLICT`
- `PRODUCT_TYPE_UNRESOLVED`

Agent 2 must never submit records containing hard blockers.

## 95. Warnings

Include:

`warnings`

Examples:

- `SEO_SOURCE_OLD`
- `OPTIONAL_IMAGE_MISSING`
- `LOW_CATEGORY_CONFIDENCE`
- `LOW_SEMANTIC_COVERAGE`

Warnings do not automatically block publication.

## 96. Source Snapshot

Every record should reference:

- `product_data_version`
- `catalog_source_version`
- `seo_version`
- `seo_source_date`
- `pricing_policy_version`
- `amazon_policy_version`
- `evidence_version`

This makes each generated listing reproducible.

## 97. Hashes

Include:

- `source_hash`
- `content_hash`
- `pricing_hash`
- `record_hash`

Hashes should help detect:

- Unchanged records
- Content-only changes
- Pricing-only changes
- Source changes

## 98. Idempotency

Each publishable record should include:

`idempotency_key`

The same unchanged logical record should result in the same idempotency identity.

Agent 2 should use it to reduce duplicate submissions.

## 99. Generation Metadata

Include:

- `generated_at`
- `generated_by_agent_version`
- `handoff_schema_version`
- `batch_id`

## 100. Rollback Reference

Where previous versions exist, include:

- `previous_record_version`
- `previous_content_hash`
- `previous_pricing_hash`

This supports controlled rollback and comparison.

## 101. Recommended Handoff JSON Structure

```json
{
  "handoff_schema_version": "1.0.0",
  "batch_id": "",
  "generated_at": "",
  "generated_by_agent_version": "",
  "internal_product_id": "",
  "sku": "",
  "marketplace": "",
  "record_version": "",
  "operation_intent": "",
  "publish_status": "",
  "identifier_mode": "",
  "identifiers": {
    "ean": null,
    "upc": null,
    "gtin": null,
    "asin": null,
    "gtin_exempt": false,
    "status": ""
  },
  "product_type": {
    "value": "",
    "status": "",
    "confidence": "",
    "locked": true
  },
  "catalog": {},
  "content": {
    "title": "",
    "item_highlights": "",
    "bullet_points": [],
    "description": "",
    "backend_search_terms": "",
    "backend_bytes": 0
  },
  "pricing": {},
  "compatibility": {},
  "claims": [],
  "evidence": [],
  "changed_fields": [],
  "unresolved_required_fields": [],
  "hard_blockers": [],
  "warnings": [],
  "versions": {},
  "audit": {},
  "hashes": {
    "source_hash": "",
    "content_hash": "",
    "pricing_hash": "",
    "record_hash": ""
  },
  "idempotency_key": "",
  "rollback": {
    "previous_record_version": null,
    "previous_content_hash": null,
    "previous_pricing_hash": null
  }
}
```

## 102. XLSX Handoff Sheet

The XLSX export should contain a dedicated `Handoff` sheet with at least:

- Handoff Schema Version
- Batch ID
- Internal Product ID
- SKU
- Marketplace
- Record Version
- Operation Intent
- Publish Status
- Identifier Mode
- Product Type
- Product Type Status
- Changed Fields
- Unresolved Required Fields
- Hard Blockers
- Warnings
- Source Hash
- Content Hash
- Pricing Hash
- Record Hash
- Idempotency Key
- Generated At
- Generated By Agent Version
