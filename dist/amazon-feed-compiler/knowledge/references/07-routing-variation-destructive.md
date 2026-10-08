# Template freshness, multi-template routing, GTIN exemption scope, variation feed, destructive operations, dry-run summary

> Source: original agent specification, sections preserved verbatim. Where this file conflicts with `SKILL.md` section "Precedence and errata", `SKILL.md` wins.

## 54. Template Freshness Control

Before using a template, inspect whether it appears current.

Track:

- template_version
- template_generation_date if present
- template_hash
- template_signature
- known latest internal mapping version
- prior template comparison

Possible status:

- `TEMPLATE_CURRENT`
- `TEMPLATE_NEW_VERSION`
- `TEMPLATE_OUTDATED_POSSIBLE`
- `TEMPLATE_VERSION_UNKNOWN`

If the template is materially different from the latest known structure:

rebuild or revalidate mappings before writing.

Do not automatically block solely because a file is old if no fresher verified template is available, but clearly warn.

## 55. Multi-Template Batch Routing

A single Agent 1 batch may contain products requiring multiple Amazon Product Types or templates.

Agent 2 must be able to:

1. group products by marketplace
2. group by Product Type
3. identify the correct template per group
4. build separate mapping/schema for each template
5. output separate feed files where required

Example:

Batch:
- 300 headphones
- 150 phone cases
- 90 chargers

Possible output:
- one HEADPHONES feed
- one PHONE_ACCESSORY feed
- one CHARGER feed

Do not force unrelated Product Types into one template.

## 56. GTIN Exemption Scope

GTIN exemption must not be treated as globally valid.

Track exemption scope where known:

- marketplace
- brand
- category
- Product Type
- account/seller context
- effective date
- source

Possible status:

- `GTIN_EXEMPTION_CONFIRMED`
- `GTIN_EXEMPTION_SCOPE_MISMATCH`
- `GTIN_EXEMPTION_UNVERIFIED`

Do not apply one GTIN exemption to unrelated products automatically.

## 57. Variation Phase 2 Feed Validation

Before writing parent/child variation feeds:

Validate:

- variation theme is supported by current template/Product Type
- parent row semantics are correct
- child identifiers are unique
- child attributes match chosen theme
- parent does not contain child-only values
- relationship fields are valid
- parent/child SKU references are consistent

Possible statuses:

- `VARIATION_FEED_READY`
- `VARIATION_THEME_INVALID`
- `PARENT_ROW_INVALID`
- `CHILD_ROW_INVALID`
- `VARIATION_REVIEW_REQUIRED`

Do not create unsupported variation relationships.

## 58. Destructive Operation Safeguards

Potentially destructive operations include:

- DELETE
- CLOSE_OFFER
- clear-value operations
- relationship removal
- mass price clearing
- offer deactivation
- inventory reset where applicable

Agent 2 must require explicit user confirmation before finalizing destructive actions.

Possible state:

`DESTRUCTIVE_ACTION_CONFIRMATION_REQUIRED`

## 59. Preview Before Destructive Actions

Before applying destructive operations, present:

- operation type
- number of affected SKUs
- affected SKU list/reference
- affected marketplace
- fields or offers to be cleared/removed
- expected consequence
- rollback reference if available

No destructive feed is marked `READY_FOR_UPLOAD` without explicit approval.

## 60. Human Dry-Run Summary

Before final feed generation, provide a concise batch summary.

Example:

- Total SKUs: 324
- Ready: 319
- Ready with warnings: 3
- Blocked: 2
- Required user questions: 2
- Invalid enums: 0
- Missing required fields: 2
- Template integrity: PASS

For large batches, detailed issues should be placed in a report rather than repeated inline.
