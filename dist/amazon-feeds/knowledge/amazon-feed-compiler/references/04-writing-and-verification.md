# Formulas/macros, integrity, capacity, provenance, dry run, cross-field, writer, reopen, validation levels

> Source: original agent specification, sections preserved verbatim. Where this file conflicts with `SKILL.md` section "Precedence and errata", `SKILL.md` wins.

## 24. Formulas, Macros and Protection

- Preserve existing formulas.
- Do not insert formulas when literal values are expected.
- Preserve XLSM/VBA when present.
- Never convert XLSM to XLSX if macros matter.
- Respect sheet protection and locked cells.
- Classify cells as:
  - USER_INPUT
  - SYSTEM_CALCULATED
  - SYSTEM_METADATA
  - LOOKUP
  - VALIDATION_SOURCE
  - EXAMPLE_ONLY
  - UNKNOWN

Write only to valid input areas.

## 25. Workbook Integrity

Do not unnecessarily:
- add columns
- delete columns
- reorder columns
- rename headers
- rename sheets
- delete metadata
- remove validations
- remove named ranges
- remove formulas
- change protected/system cells
- alter macros
- rebuild Amazon formatting
- remove hidden system structures

Rule:
Populate cells. Do not redesign Amazon's workbook.

## 26. Row Capacity and File Splitting

Determine safe template capacity.

If batch exceeds safe capacity:
1. extend rows only if validations/formatting/formulas can be preserved safely, or
2. split into multiple feed files

Example:
- Feed_DE_001.xlsx
- Feed_DE_002.xlsx
- Feed_DE_003.xlsx

Each file must include:
- batch_id
- part_number
- SKU count
- marketplace
- template fingerprint
- source versions

## 27. Row and Cell Provenance

Maintain:
SKU → Amazon Row

For every populated cell store:
- Agent 1 source path
- Amazon field
- worksheet
- cell coordinate
- input value
- output value
- transformation type
- mapping confidence

Example:
marketplaces.DE.content.title
→ item_name
→ Template
→ K7

## 28. Mutation Log

Record every transformation.

Example:
Input: 0.5 kg
Output: 500
Unit: g
Transformation: UNIT_NORMALIZATION
Meaning Changed: NO

Example:
Input: Male
Output: accepted localized enum
Transformation: ENUM_MAPPING
Meaning Changed: NO

If meaning could change:
USER_DECISION_REQUIRED

## 29. Pre-Fill Dry Run

Before writing, calculate:

- detected fields
- required fields
- available required fields
- missing required fields
- valid mappings
- ambiguous mappings
- invalid enums
- hard blockers
- warnings

If hard blockers exist, do not mark output READY_FOR_UPLOAD.

## 30. Cross-Field Validation

Validate relationships:
- GTIN type ↔ GTIN format/length
- Price ↔ Currency
- Sale Price ↔ Sale Dates
- Weight ↔ Weight Unit
- Dimensions ↔ Dimension Unit
- Battery status ↔ Battery attributes
- Variation Theme ↔ Child attributes
- Country of Origin ↔ accepted country enum
- Product Type ↔ required attributes
- Identifier Mode ↔ product ID fields
- Operation Intent ↔ populated fields

## 31. Feed Writer

Only after successful dry run:
- populate approved fields
- preserve template structure
- preserve validations
- preserve formulas
- preserve named ranges
- preserve macros
- preserve metadata
- preserve row mapping
- preserve identifier formatting
- respect operation intent

## 32. Reopen and Verify

After save:
1. close workbook
2. reopen generated file
3. re-read written values
4. verify workbook structure
5. verify identifiers
6. verify prices
7. verify row alignment
8. verify formulas
9. verify validations
10. verify hidden/grouped structure
11. verify macros where applicable
12. verify named ranges

Status:
- REOPEN_VALIDATED
- POST_WRITE_VALIDATION_FAILED

## 33. Workbook Integrity Comparison

Compare pre-fill and post-fill:
- sheet count
- sheet names
- headers
- metadata
- named ranges
- validations
- formulas
- protection
- hidden/grouped structure
- macros
- template signature/hash

If unintended structure changed:
TEMPLATE_STRUCTURE_MODIFIED

Do not mark ready.

## 34. Validation Levels

L1 — Workbook Integrity  
L2 — Template Schema  
L3 — Field/Data Validation  
L4 — Cross-Field Business Logic

READY_FOR_UPLOAD requires all hard checks to pass.
