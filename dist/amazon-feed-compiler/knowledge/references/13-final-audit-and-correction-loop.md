# Final readiness gate, full audit, violation report, correction loop

> Source: original agent specification, sections preserved verbatim. Where this file conflicts with `SKILL.md` section "Precedence and errata", `SKILL.md` wins.

## 118. Final Readiness Gate

After the feed file is generated, Agent 2 must perform a complete final integrity and correctness audit before the file can be considered upload-ready.

There are only two final file-level readiness states:

- `READY_FOR_AMAZON_UPLOAD`
- `NOT_READY_FOR_AMAZON_UPLOAD`

If ANY hard rule, required condition, structural rule, data rule, mapping rule, validation rule, workbook-integrity rule, identifier rule, pricing rule, enum rule, or user-approved condition is violated:

the entire file status must become:

`NOT_READY_FOR_AMAZON_UPLOAD`

There is no partial "ready" state for the final file.

## 119. Mandatory Post-Generation Full Audit

After the workbook is written and saved, Agent 2 must:

1. Close the generated workbook
2. Reopen the generated workbook
3. Re-read the entire relevant Template data area
4. Re-check workbook integrity
5. Re-check all non-Template sheets for unintended changes
6. Re-check rows 1–6
7. Re-check row 6 example/reference integrity
8. Re-check every populated row from row 7 onward
9. Re-check every populated field
10. Re-check all required fields
11. Re-check all conditionally required fields
12. Re-check all enums
13. Re-check all identifiers
14. Re-check all prices and currencies
15. Re-check all dates
16. Re-check all units
17. Re-check all content fields
18. Re-check all operation-intent semantics
19. Re-check all cross-field dependencies
20. Re-check formula injection protection
21. Re-check row uniqueness
22. Re-check product-to-row alignment
23. Re-check mapping provenance
24. Re-check template fingerprint / structure
25. Re-check approval hash where approval is required

This is the final mandatory QA gate.

## 120. Final Audit Scope

The final audit must validate at minimum:

## Workbook Integrity
- workbook opens successfully
- correct file type preserved
- macros preserved where applicable
- no corruption
- no missing sheets
- no renamed sheets
- no reordered sheets if prohibited
- no unintended visibility changes
- no broken formulas
- no broken named ranges
- no broken validations
- no altered protection outside intended scope

## Non-Template Sheet Integrity
- no values changed
- no formulas changed
- no formatting changed
- no validation changed
- no named ranges changed
- no visibility changed
- no protection changed
- no structural mutation

## Template Integrity
- rows 1–6 unchanged
- row 6 unchanged
- row 6 still treated as Amazon example/reference row
- only approved input cells from row 7 downward changed
- no unintended formatting or system-cell changes
- no row drift
- no accidental overwrites

## Data Integrity
- correct SKU
- correct EAN / UPC / GTIN / ASIN handling
- correct GTIN exemption behavior
- correct Product Type
- correct marketplace
- correct currency
- correct country of origin
- correct compatibility
- correct content
- correct pricing
- correct quantity tiers
- correct operation intent

## Schema Compliance
- required fields populated
- conditionally required fields satisfied
- valid data types
- accepted enums
- valid units
- valid lengths
- valid occurrence counts
- valid dependencies
- valid update semantics

## Agent 1 Handoff Integrity
- no unauthorized meaning changes
- source values mapped correctly
- changed_fields respected
- locked fields respected
- blocked records not inserted as upload-ready
- approval scope respected

## 121. Any Violation = NOT READY

If one or more violations are found:

Set:

`file_status = NOT_READY_FOR_AMAZON_UPLOAD`

Do not present the file as final or upload-ready.

Do not silently correct meaning-critical issues.

Do not hide violations.

Do not downgrade a hard violation to a warning merely to complete the file.

## 122. Violation Report

When the file is NOT READY, Agent 2 must produce a detailed violation report.

For every violation include where applicable:

- Severity
- Error Code
- SKU
- Amazon Row
- Worksheet
- Column Letter
- Column Header
- Amazon Field
- Cell Coordinate
- Current Value
- Expected / Allowed Value
- Agent 1 Source Path
- Source Value
- Violation Description
- Why It Matters
- Proposed Correction
- Correction Type
- Whether Meaning Changes
- Whether User Confirmation Is Required

Example structure:

| Severity | SKU | Row | Column | Field | Current Value | Issue | Proposed Fix |
|---|---|---:|---|---|---|---|---|
| BLOCKER | ABC123 | 14 | K | item_name | ... | Title exceeds limit | Shorten title |
| BLOCKER | ABC124 | 15 | B | external_product_id | 12345 | Invalid EAN length | User input required |
| BLOCKER | ABC125 | 16 | AQ | country_of_origin | blank | Required field missing | Provide country |

## 123. Violation Grouping

For large batches, Agent 2 should group similar violations.

Examples:

- 47 rows missing Country of Origin
- 18 rows with invalid enum in the same column
- 7 rows with duplicate GTIN
- 3 rows with sale date errors

Provide:

- summary by issue type
- affected row range / SKU list
- detailed report artifact

Avoid asking the same correction question dozens of times.

## 124. Correction Approval Workflow

If the file is NOT READY:

1. Agent 2 displays the violations
2. Agent 2 proposes corrections
3. Agent 2 identifies which corrections are safe and which require user decision
4. Agent 2 waits for user confirmation for any correction that requires approval
5. Agent 2 applies only approved corrections
6. Agent 2 regenerates the affected file/rows
7. Agent 2 reruns the FULL final audit
8. Agent 2 produces a new file version

No file becomes upload-ready merely because corrections were applied.

The corrected file must pass the entire audit again.

## 125. Safe vs Approval-Required Corrections

## Safe corrections may include:

- exact enum normalization
- exact unit formatting
- exact date formatting
- whitespace cleanup
- safe decimal formatting
- safe boolean formatting
- formula-injection neutralization
- preserving leading zeros
- restoration of intended cell text type
- restoration of workbook state where no product meaning changes

## User approval required for:

- Product Type change
- identifier correction
- GTIN / UPC / EAN replacement
- Country of Origin
- model change
- compatibility change
- pack quantity change
- claim change
- content meaning change
- price logic change
- operation intent change
- variation structure change
- catalog conflict resolution
- destructive action

If uncertain whether meaning changes:

treat correction as approval-required.

## 126. Correction Versioning

Every correction cycle must create a new version.

Example:

`Feed_DE_B20261006_v1.xlsx`
→ NOT READY

after approved correction:

`Feed_DE_B20261006_v2.xlsx`

Store:

- prior version
- correction reason
- corrected fields
- user approval reference
- new hashes
- new validation result

Never overwrite the prior failed version silently.

## 127. Revalidation After Correction

After every correction cycle, rerun:

- L1 Workbook Integrity
- L2 Template Schema
- L3 Field/Data Validation
- L4 Cross-Field Business Logic
- Full Post-Generation Audit

Do not run only a partial check on the corrected field.

A correction may create a downstream conflict.

## 128. Final Ready State

Only after zero unresolved hard violations remain may Agent 2 set:

`file_status = READY_FOR_AMAZON_UPLOAD`

Final summary should include:

- Total rows checked
- Total SKUs checked
- Hard violations: 0
- Unresolved required fields: 0
- Invalid enums: 0
- Identifier conflicts: 0
- Price conflicts: 0
- Workbook scope violations: 0
- Non-Template mutations: 0
- Rows 1–6 modifications: 0
- Template integrity: PASS
- Data integrity: PASS
- Final audit: PASS

## 129. Final File Delivery Rule

Agent 2 must never label or deliver a file as ready for Amazon upload before the full audit passes.

If violations exist:

deliver the file only as:

`NOT_READY_FOR_AMAZON_UPLOAD`

and accompany it with:

- violation report
- proposed fixes
- required user confirmations
- affected rows/columns/cells

After user confirmation and corrections:

produce a NEW corrected file
→ rerun full audit
→ only then mark READY_FOR_AMAZON_UPLOAD if all checks pass.

## 130. Final QA Loop

Final mandatory loop:

Generate Feed
→ Save
→ Close
→ Reopen
→ Full Integrity Audit
→ Full Data Audit
→ Violations?

YES
→ NOT_READY_FOR_AMAZON_UPLOAD
→ Show exact rows / columns / cells / values / issues
→ Ask for required approval
→ Apply approved corrections
→ Create new file version
→ Full audit again

NO
→ READY_FOR_AMAZON_UPLOAD

This loop continues until either:

- the file passes all checks, or
- the user stops the correction process.
