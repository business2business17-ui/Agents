# Workbook inspection, data start row, fingerprint, sheet roles, Data Definitions, valid values, enums

> Source: original agent specification, sections preserved verbatim. Where this file conflicts with `SKILL.md` section "Precedence and errata", `SKILL.md` wins.

## 5. Workbook Inspector

Before writing anything, inspect:

- filename
- file type: XLSX / XLSM
- sheet count
- sheet names
- sheet visibility
- very hidden sheets where supported
- hidden rows
- hidden columns
- grouped/collapsed rows
- grouped/collapsed columns
- merged cells
- freeze panes
- filters
- tables
- named ranges
- data validations
- formulas
- protected sheets
- locked cells
- editable ranges
- sample rows
- last used row
- last used column
- workbook defined names
- macros/VBA presence
- external references where present

No feed writing before inspection is complete.

## 6. Dynamic Data Start Row

Never assume row 7.

Detect:
- metadata rows
- version/signature rows
- human-readable header rows
- machine/internal header rows
- example/sample rows
- first true product-entry row

Store:
- data_start_row
- header_row
- machine_header_row if applicable
- last_template_column

Status:
- DATA_START_CONFIRMED
- DATA_START_REVIEW_REQUIRED

## 7. Full Template Expansion for Analysis

For analysis, inspect the complete logical workbook:

- unhide hidden columns
- inspect grouped/collapsed columns
- unhide hidden rows
- inspect grouped/collapsed rows
- inspect hidden/very-hidden sheets
- scan from column A to actual last template column

Preserve original visibility state and restore it in the final workbook unless explicitly instructed otherwise.

## 8. Template Fingerprint

Create and store:

- template_hash
- template_signature if present
- template_version
- template_marketplace
- template_language
- template_product_type
- template_file_type
- sheet_structure_hash
- header_hash
- validation_hash

Include fingerprint in final manifest.

## 9. Localized Sheet Detection

Do not identify sheets only by exact English names.

Detect semantic roles such as:
- TEMPLATE_DATA
- DATA_DEFINITIONS
- VALID_VALUES
- INSTRUCTIONS
- EXAMPLES
- METADATA
- LOOKUP
- SYSTEM
- UNKNOWN

Sheet roles must be inferred from structure, headers, definitions, examples, validation references, and known template patterns.

If a critical sheet role cannot be resolved safely, ask the user or return BLOCKED_TEMPLATE.

## 10. Data Definitions Parser

Parse the Data Definitions equivalent and extract, where available:

- internal field name
- localized display name
- definition
- requirement status
- data type
- example
- accepted values
- min/max
- max/min length
- unit expectations
- dependencies
- repeatability
- max occurrences
- conditional requirements
- product-type applicability
- marketplace applicability
- notes

Build an internal AMAZON_TEMPLATE_ATTRIBUTE_SCHEMA.

## 11. Requirement Classification

Classify fields as:
- REQUIRED
- CONDITIONALLY_REQUIRED
- RECOMMENDED
- OPTIONAL
- SYSTEM_ONLY
- NOT_APPLICABLE

Conditional fields must be represented in a dependency graph.

Example:
has_battery = true
→ battery_type
→ battery_composition
→ battery_weight

## 12. Instructions / Examples / Valid Values

Instructions sheet:
- parse workflow rules
- update behavior
- upload restrictions
- formatting requirements
- category-specific notes
- macro instructions

Examples sheet:
- use as supporting evidence for format and structure
- never let examples override explicit definitions/validations

Valid values:
resolve from all available sources:
1. Data Definitions
2. Valid Values sheet
3. Excel validation lists
4. Named ranges
5. Inline validation lists
6. Lookup sheets
7. Formula-based validation references

## 13. Data Validation and Named Ranges

Inspect validation rules:
- list
- whole number
- decimal
- date
- text length
- custom formula

Store:
- validation type
- source/range
- allowed values
- min/max
- formula
- affected ranges

Resolve named ranges such as:
Cell → Validation → Named Range → Accepted Values

## 14. Enum Resolver

Agent 1 may provide canonical semantic values while Amazon requires template-specific or localized accepted values.

Resolve:

Canonical Meaning
→ Valid Values
→ Exact Accepted Amazon Value

Do not simply translate.

Statuses:
- ENUM_MAPPED
- ENUM_AMBIGUOUS
- ENUM_INVALID
- ENUM_USER_DECISION_REQUIRED

If ambiguous, ask the user.
