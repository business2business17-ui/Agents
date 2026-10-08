# Determinism, recovery, secrets, PII, corrupted templates, unicode, whitespace, length, formula injection, reconciliation, ready criteria

> Source: original agent specification, sections preserved verbatim. Where this file conflicts with `SKILL.md` section "Precedence and errata", `SKILL.md` wins.

## 61. Deterministic Output

Given the same:

- Agent 1 package
- Amazon template
- mapping version
- user override rules
- pricing data
- configuration

Agent 2 should generate the same logical feed output.

Avoid:

- random field ordering
- unstable row ordering
- nondeterministic mappings
- timestamp-dependent content fields unless metadata-only

Deterministic output is required for:

- reproducibility
- hashing
- Git diffs
- rollback
- audit

## 62. Recovery and Checkpointing

For large batches, store checkpoints after major stages:

- TEMPLATE_INSPECTED
- SCHEMA_PARSED
- MAPPING_CREATED
- QUESTIONS_RESOLVED
- DRY_RUN_VALIDATED
- FEED_WRITTEN
- REOPEN_VALIDATED

If processing is interrupted, resume from the latest compatible checkpoint rather than rebuilding the entire batch.

Checkpoint compatibility must depend on hashes/versions of:

- template
- Agent 1 source
- mapping
- override rules

## 63. Security and Secrets

Never write secrets into:

- XLSX/XLSM
- JSON
- JSONL
- manifests
- issue reports
- Git repositories
- mutation logs
- provenance logs

Secrets include:

- API credentials
- refresh tokens
- access tokens
- client secrets
- passwords
- secret keys

If submission credentials are ever required by a future integration, keep them outside feed artifacts and audit files.

## 64. PII Hygiene

Do not unnecessarily duplicate personal/customer/contact data into:

- provenance
- mutation logs
- validation reports
- Git history
- public artifacts

Store only data needed for the feed workflow.

If a template contains personal information not required for the current task:

do not replicate it into unrelated outputs.

## 65. Corrupted Template Handling

If the workbook is structurally damaged, unreadable, partially corrupted, or validations cannot be reliably interpreted:

do not repair it by guesswork.

Possible states:

- `TEMPLATE_CORRUPTED`
- `TEMPLATE_VALIDATION_UNREADABLE`
- `TEMPLATE_MACRO_INTEGRITY_UNKNOWN`
- `TEMPLATE_REPLACEMENT_REQUIRED`

Ask the user for a clean template if necessary.

## 66. Unicode and Locale-Safe String Handling

Preserve Unicode correctly across:

- German umlauts
- French accents
- Italian characters
- Spanish characters
- Polish characters
- Dutch
- Swedish
- Japanese
- Arabic
- other supported marketplace languages

Ensure UTF-8 safe handling for JSON/JSONL.

When writing Excel, verify that text round-trips without corruption.

## 67. Whitespace and Hidden Character Normalization

Before writing text fields, inspect for:

- leading spaces
- trailing spaces
- repeated spaces
- non-breaking spaces
- hidden line breaks
- tabs
- carriage returns
- control characters
- zero-width characters where relevant

Normalize only when doing so does not change intended content.

Log meaningful transformations.

## 68. Cell Length Validation

Validate both:

1. Amazon semantic limits
2. template/data-validation limits

Examples:

- title length
- bullet length
- backend keywords bytes
- model length
- SKU length
- attribute text length

If content exceeds a hard limit:

do not silently truncate meaning-critical data.

Return:

`FIELD_LENGTH_EXCEEDED`

Use approved shortening logic or ask the user where necessary.

## 69. Excel Formula Injection Protection

Any text value beginning with characters that Excel may interpret as a formula must be handled safely.

Risk prefixes include:

- `=`
- `+`
- `-`
- `@`

When the value is intended as literal text:

- preserve the semantic text
- prevent Excel from executing it as a formula
- use safe text formatting/escaping supported by the workbook library
- verify after reopen that the stored value is text, not a formula

This is especially important for:

- SKU
- model
- part numbers
- product text
- user-provided free text

Never allow external input to create unintended formulas.

## 70. Processing Report Error Correction Policy

Auto-correct only when the fix is meaning-preserving and deterministic, such as:

- accepted enum substitution with exact semantic equivalence
- unit formatting
- decimal formatting
- date formatting
- boolean formatting
- safe whitespace cleanup

Require user or Agent 1 review when correction would change:

- product identity
- product type
- brand
- model
- compatibility
- pack size
- country of origin
- claims
- price logic
- variation structure

## 71. Upload Result Reconciliation

After Processing Report ingestion, classify the batch:

- `BATCH_ACCEPTED`
- `BATCH_ACCEPTED_WITH_WARNINGS`
- `BATCH_PARTIALLY_ACCEPTED`
- `BATCH_REJECTED`
- `BATCH_PROCESSING_UNKNOWN`

Produce summary:

- total submitted
- accepted
- accepted with warning
- rejected
- unresolved
- auto-fixable
- user-review-required
- Agent-1-review-required

## 72. Updated Ready-for-Upload Criteria

A feed may be marked `READY_FOR_UPLOAD` only if:

- template inspection passed
- template fingerprint exists
- schema parsed
- required mappings resolved
- required attributes populated
- enums valid
- identifier logic valid
- pricing logic valid
- operation intent valid
- blank/update semantics resolved
- no unresolved hard blockers
- workbook integrity preserved
- formulas/macros/named ranges preserved where applicable
- Unicode/text round-trip verified
- formula-injection risks neutralized
- feed successfully reopened
- written values verified
- manifest created
- mapping report created
- validation report created
- destructive operations explicitly approved where relevant

## 73. Updated Final Architecture

Agent 2 pipeline:

Receive Agent 1 Package
→ Inspect Workbook
→ Reveal/Analyze Full Structure
→ Fingerprint Template
→ Check Template Freshness
→ Detect Localized Sheet Roles
→ Parse Instructions
→ Parse Data Definitions
→ Resolve Valid Values / Dropdowns / Named Ranges
→ Build Amazon Template Schema
→ Route by Marketplace / Product Type / Template
→ Map Agent 1 Fields
→ Evaluate Mapping Confidence
→ Run Clarification Engine
→ Resolve Operation Intent / Blank Semantics
→ Dry-Run Validate
→ Human Summary
→ Write Feed
→ Reopen
→ Verify Workbook
→ Generate Manifest
→ Generate Mapping
→ Generate Validation Report
→ READY_FOR_UPLOAD

Mandatory post-upload loop:

Amazon Processing Report
→ Upload Result Reconciliation
→ Error Taxonomy
→ SKU / Row / Field / Cell Provenance
→ Safe Auto-Fix OR User Question OR Agent 1 Review
→ Incremental Feed Regeneration
→ Revalidation
