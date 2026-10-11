# Core rules, inputs, Agent 1 status handling, state machine

> Source: original agent specification, sections preserved verbatim. Where this file conflicts with `SKILL.md` section "Precedence and errata", `SKILL.md` wins.

## 1. Core Rules

- Never fill before inspecting the template.
- Never hardcode the first data row.
- Never assume English sheet names.
- Never assume visible rows/columns are the full template.
- Never map by header similarity alone.
- Never invent valid values.
- Never translate Amazon enums arbitrarily.
- Never silently alter Agent 1 product meaning.
- Never silently alter identifiers, prices, country of origin, compatibility, product type, claims, or operation intent.
- Never destroy workbook validations, formulas, named ranges, metadata, protection, macros, or hidden structures.
- Never overwrite the original Amazon template.
- Ask the user whenever a missing decision materially affects identity, meaning, compliance, publication eligibility, pricing, catalog structure, update semantics, or variation structure.

## 2. Inputs

Agent 2 may receive:

### Required
- Amazon feed template workbook
- Agent 1 canonical package
- Target marketplace

### Usually available
- Agent 1 JSON / JSONL
- Agent 1 XLSX review export
- Product Type selected by Agent 1
- Operation intent
- Publish status
- SKU
- EAN / UPC / GTIN / ASIN / GTIN exemption state
- Content
- Catalog attributes
- Pricing
- Claims/compliance status
- Compatibility
- Country of Origin
- Source versions
- Hashes

### Optional
- Existing mappings
- Prior Amazon feed
- Prior Processing Report
- Template fingerprints
- User override rules
- Marketplace configuration
- Repository location

## 3. Agent 1 Status Handling

Automatically process:
- READY_TO_PUBLISH

Conditionally process if configured:
- READY_WITH_WARNINGS

Do not automatically produce upload-ready rows for:
- NEEDS_REVIEW
- DATA_REQUIRED
- POLICY_RISK
- PRICE_CONFLICT
- BLOCKED

Blocked records must remain visible in issue reports.

## 4. State Machine

RECEIVED
→ TEMPLATE_INSPECTED
→ SCHEMA_PARSED
→ MAPPING_CREATED
→ QUESTIONS_REQUIRED?
→ WAITING_FOR_USER_INPUT if needed
→ DRY_RUN_VALIDATED
→ FEED_WRITTEN
→ REOPEN_VALIDATED
→ READY_FOR_UPLOAD

Blocked states:
- BLOCKED_TEMPLATE
- BLOCKED_MAPPING
- BLOCKED_REQUIRED_DATA
- BLOCKED_ENUM
- BLOCKED_IDENTIFIER
- BLOCKED_VALIDATION
- BLOCKED_WORKBOOK_INTEGRITY
- BLOCKED_USER_DECISION_REQUIRED
