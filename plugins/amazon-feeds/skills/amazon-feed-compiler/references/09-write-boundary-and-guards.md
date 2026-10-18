# Fixed write boundary, row 6, scope, text hygiene layer, simulation, strict mode, criticality, guards, locks, approval snapshot

> Source: original agent specification, sections preserved verbatim. Where this file conflicts with `SKILL.md` section "Precedence and errata", `SKILL.md` wins.

## 74. Fixed Template Write Boundary

For this workflow, the Amazon Template sheet uses row 7 as the first product-data row.

Agent 2 must therefore enforce:

- Rows 1–6 are READ-ONLY.
- Do not write, clear, merge, reformat, rename, or otherwise modify rows 1–6.
- Product data entry begins at row 7.
- Row 7 is the first allowed product row.
- Subsequent SKUs continue downward from row 7.
- If the workbook structure indicates that row 7 is not a valid product-entry row, STOP and return:
  `TEMPLATE_ROW7_CONFLICT`

Do not silently shift the start row.

This workflow rule overrides generic dynamic-row assumptions for the current Agent 2 configuration.

Agent 2 may inspect rows 1–6 for understanding, but must never modify them.

## 74A. Row 6 — Amazon Example Row

In this workflow, row 6 usually contains an Amazon example/example-product record showing how product data should be formatted.

Agent 2 must treat row 6 as:

- reference data
- formatting guidance
- example-value guidance
- possible enum/value-format illustration
- possible relationship between visible headers and expected cell content

Agent 2 must NOT treat row 6 as:

- a real user SKU
- a row to overwrite
- a row to delete
- a row to copy blindly
- authoritative product data for the current batch

Rules:

- Row 6 is READ-ONLY.
- Analyze row 6 together with Data Definitions, Valid Values, Instructions and Excel validation rules.
- Use row 6 only as supporting evidence for understanding field formatting and structure.
- Formal Data Definitions / validation rules take precedence over row 6 if they conflict.
- Do not inherit product-specific values from row 6 into real SKUs.
- Product data entry still begins at row 7.

Possible status:

`ROW6_EXAMPLE_DETECTED`

If row 6 appears not to be an example row in a specific template, do not assume otherwise; flag:

`ROW6_ROLE_REVIEW_REQUIRED`

## 75. Template Sheet Write Scope

Agent 2 may write product feed data only to the designated Amazon `Template` data sheet.

Other sheets may be READ for:

- Data Definitions
- Valid Values
- Instructions
- Examples
- Lookup values
- Named ranges
- Validation references
- Metadata
- System logic

But Agent 2 must not modify other sheets.

Hard rule:

`READ_OTHER_SHEETS = TRUE`
`WRITE_OTHER_SHEETS = FALSE`

Do not modify:

- Data Definitions
- Valid Values
- Instructions
- Examples
- Lookup sheets
- Metadata sheets
- Hidden sheets
- System sheets

If the Template relies on formulas or references to those sheets, preserve them exactly.

## 76. Workbook Preservation Scope

Agent 2 must preserve:

- Rows 1–6 exactly
- All non-Template sheets exactly
- Sheet order
- Sheet names
- Hidden/visible states
- Named ranges
- Validations
- Formulas
- Macros
- Protection
- Metadata
- Formatting outside the intended product-data cells

Only product-entry cells on the Template sheet from row 7 downward may be populated or updated.

If any unintended workbook mutation occurs:

`WORKBOOK_SCOPE_VIOLATION`

The output must not be marked `READY_FOR_UPLOAD`.

## 77. Human-Quality Output Layer

Agent 2 should preserve natural, professional, human-readable product content produced by Agent 1.

Goals:

- avoid mechanical-looking formatting
- avoid repetitive boilerplate
- preserve natural localized wording
- preserve category-appropriate phrasing
- avoid unnecessary templated repetition across SKUs
- maintain clean spacing and punctuation
- keep values consistent with how a careful human operator would enter them

This layer is for content quality and readability only.

Agent 2 must NOT:

- falsify authorship
- spoof manual entry
- manipulate timestamps or metadata to imitate a human operator
- intentionally evade Amazon automation/bot detection
- bypass platform controls
- conceal prohibited automation

If Amazon requires disclosure, account permissions, API use, or another approved workflow, those requirements take precedence.

Use the status:

`HUMAN_QUALITY_CHECK = PASS / REVIEW_REQUIRED`

not any anti-detection or evasion status.

## 78. Simulation Mode

Support:

`SIMULATION_MODE = ON`

In Simulation Mode, Agent 2 performs:

- template inspection
- schema parsing
- mapping
- validation
- question generation
- dry-run summary
- row planning
- expected cell mapping

But does not produce a final modified upload workbook.

Output:

- mapping report
- blockers
- warnings
- unresolved fields
- expected row assignments
- proposed transformations
- approval preview

## 79. Strict Mode

Default recommended setting:

`STRICT_MODE = ON`

Behavior:

- HIGH confidence → may process automatically
- MEDIUM confidence → requires review unless explicitly whitelisted
- LOW confidence → blocker
- meaning-changing transformations → blocker
- ambiguous enums → blocker
- ambiguous mapping → blocker

Strict Mode should be used for early production deployments and high-risk categories.

## 80. Field Criticality

Classify mapped fields as:

- `IDENTITY_CRITICAL`
- `COMPLIANCE_CRITICAL`
- `OFFER_CRITICAL`
- `CONTENT_CRITICAL`
- `OPTIONAL`

Examples:

IDENTITY_CRITICAL:
- GTIN
- Brand
- Model
- Product Type
- Pack Quantity

COMPLIANCE_CRITICAL:
- Country of Origin
- Battery information
- Safety attributes
- Regulated claims

OFFER_CRITICAL:
- Price
- Currency
- Sale dates
- Quantity
- Condition

Criticality affects validation severity and clarification behavior.

## 81. Row Uniqueness Guard

Within one feed file, the combination:

`marketplace + SKU`

must be unique unless the specific Amazon template explicitly requires multiple rows for one SKU.

If duplicate rows are detected unexpectedly:

`DUPLICATE_FEED_ROW`

Do not publish until resolved.

## 82. Duplicate Submission Guard

Before creating a final feed, compare:

- record_hash
- idempotency_key
- marketplace
- SKU
- operation intent

against prior generated/submitted batches.

If the exact same logical payload was already generated:

`DUPLICATE_SUBMISSION_POSSIBLE`

Warn the user before producing another upload-ready copy when duplicate submission could create unnecessary reprocessing.

## 83. Manual Field Locks

Allow fields to be marked:

`DO_NOT_CHANGE`

Examples:

- title
- brand
- model
- country_of_origin
- price
- compatibility

Agent 2 must not modify locked fields unless the user explicitly removes the lock.

Store:

- field
- scope
- reason
- locked_by
- locked_at
- version

## 84. Source Freshness Flags

Track freshness not only for the Amazon template but also for Agent 1 data.

Possible flags:

- `SEO_OLD`
- `PRICE_OLD`
- `CATALOG_OLD`
- `TTX_OLD`
- `TTX_UPDATED_AFTER_FEED_BUILD`
- `AGENT1_PACKAGE_UPDATED_AFTER_APPROVAL`

Freshness warnings should not automatically alter values.

## 85. Approval Snapshot

After user approval of a dry-run or batch preview, store:

- `approved_by_user = true`
- `approved_batch_hash`
- `approved_record_hashes`
- `approved_at`
- `approval_scope`

Before final feed generation, recompute relevant hashes.

If approved data changed:

`APPROVAL_INVALIDATED`

Require renewed approval for affected records.

## 86. Submission Package Checksum

Bind the final delivery artifacts together with one package checksum.

Package should include:

- Amazon feed file
- manifest
- mapping report
- validation report
- provenance reference

Store:

`submission_package_checksum`

This allows Processing Reports and later audits to be linked to the exact generated feed package.

## 87. Updated Final Hard Boundary

For this configured workflow:

- Product data writing starts on Template row 7.
- Rows 1–6 are never modified.
- Other sheets are read-only.
- Only intended Template cells from row 7 downward may be changed.
- Any violation blocks `READY_FOR_UPLOAD`.
