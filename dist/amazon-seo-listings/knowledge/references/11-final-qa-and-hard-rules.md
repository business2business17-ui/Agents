# Final quality check, hard rules, architecture

> Source: original agent specification, sections preserved verbatim. Where this file conflicts with `SKILL.md` section "Precedence and errata", `SKILL.md` wins.

## 103. Final Quality Check

Before output validate:

## Title

- Applicable length respected
- No meaningful word >2 repetitions
- Factual
- Localized
- No unsupported claim
- No prohibited term

## SEO

- Marketplace-specific
- Competitor brands removed
- Irrelevant terms removed
- No keyword stuffing

## Backend

- <250 UTF-8 bytes
- No prohibited terms
- No competitor brands

## Catalog

- Product Type valid
- Required attributes checked
- Identifier state valid
- Origin verified when available

## Claims

- Every claim classified
- Unsupported claims excluded
- Regulated claims flagged

## Compatibility

- Evidence-supported
- Not broader than verified data

## Pricing

- Correct base price
- User input preserved
- Formulas correct
- Rounding correct
- Currency valid
- Pricing does not leak into SEO copy

## Images

- Image-to-SKU matching checked
- Additional images requested only when needed

## Versioning

- Versions updated
- Audit preserved
- Diff generated when applicable

## Handoff

- Schema version present
- Operation intent present
- Publish status present
- Hard blockers resolved or record blocked
- Product Type lock set
- Hashes generated
- Idempotency key generated

## 104. Final Hard Rules

Verified Product TTX wins over SEO.

Verified packaging evidence may support or challenge TTX, but conflicts must be surfaced.

Amazon policy wins over SEO.

Product Type rules win over universal assumptions.

Explicit user data wins over calculated values.

Never silently change identifiers.

Never fabricate:

- GTIN
- UPC
- EAN
- ASIN
- Country of Origin
- Compatibility
- Technical characteristics
- Claims
- MSRP
- MAP
- Sale dates
- Pricing percentages

Never use competitor trademarks merely for SEO.

Never copy competitor listing text.

Never create variation relationships without validation.

Never regenerate unaffected fields unnecessarily.

Never treat SEO data as product evidence.

Never publish high-risk inferred values without approval.

Agent 1 must produce data that is:

- Accurate
- Traceable
- Marketplace-specific
- Scalable
- Versioned
- Auditable
- Compliant
- SEO-optimized
- Feed-ready
- Agent-2-ready

## 105. Final System Architecture

Agent 1 pipeline:

`Ingest → Normalize → Validate → Evidence Matrix → Claims → Category → Attributes → Compatibility → SEO → Content → Pricing → Image Readiness → QA → Publish Status → Versioning → JSON/JSONL → XLSX → GitHub → Agent 2 Handoff`

Phase 2 variation pipeline:

`Parent Candidate Detection → Variation Theme Validation → Child Validation → Parent/Child Data → Relationship Handoff`

Agent 2 future pipeline:

`Agent 1 Canonical Package → Amazon PTD Resolution → Exact Field Mapping → Amazon Enumeration Mapping → Feed/API Payload → Validation → Submission`

Agent 2 may transform format.

Agent 2 must not change product meaning.

If a required Amazon transformation would materially alter the product meaning, Agent 2 must stop and return:

`AGENT1_DATA_REVIEW_REQUIRED`
