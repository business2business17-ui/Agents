# Fill method, strict worksheet mutation boundary, integrity check, fill sequence

> Source: original agent specification, sections preserved verbatim. Where this file conflicts with `SKILL.md` section "Precedence and errata", `SKILL.md` wins.

## 111. Humanizer Fill Method

Agent 2 must use a `HUMANIZER_FILL_METHOD` for the actual population of the Amazon Template sheet.

Purpose:

- make the completed feed look clean, consistent and naturally prepared
- preserve normal human-entered formatting conventions
- avoid mechanical artifacts caused by bulk processing
- normalize spacing, punctuation and value presentation where safe
- preserve readable localized content from Agent 1
- keep row-by-row data coherent and non-random
- avoid accidental duplicated boilerplate caused by automation
- preserve intended capitalization and category-appropriate wording

The Humanizer layer may perform only meaning-preserving transformations.

Allowed examples:

- normalize redundant spaces
- remove accidental trailing spaces
- normalize safe line breaks
- preserve local punctuation conventions
- preserve natural text casing
- ensure text fields do not contain machine artifacts
- ensure identifiers remain exact
- ensure values are written in the format required by the template
- ensure product rows look consistently and carefully completed

The Humanizer layer must NOT:

- fabricate product facts
- rewrite verified claims
- alter identifiers
- alter pricing logic
- change Product Type
- change compatibility
- change Country of Origin
- invent missing values
- randomize content merely to appear human
- spoof manual-entry metadata
- falsify authorship
- manipulate timestamps to imitate human activity
- bypass Amazon controls
- evade platform detection or enforcement

The Humanizer method is a quality and presentation layer only.

Possible status:

- `HUMANIZER_PASS`
- `HUMANIZER_REVIEW_REQUIRED`
- `HUMANIZER_BLOCKED_BY_DATA_CONFLICT`

## 112. Strict Worksheet Mutation Boundary

Only the Amazon `Template` sheet may be modified.

All other workbook sheets are strictly READ-ONLY.

This includes, without limitation:

- Data Definitions
- localized Data Definitions equivalents
- Valid Values
- Instructions
- Examples
- Lookup sheets
- Metadata sheets
- hidden sheets
- very hidden sheets
- system sheets
- support/reference sheets

Rules:

`READ_NON_TEMPLATE_SHEETS = TRUE`
`WRITE_NON_TEMPLATE_SHEETS = FALSE`

Agent 2 may:

- read cell values
- inspect formulas
- inspect named ranges
- inspect validation sources
- inspect examples
- inspect metadata
- inspect hidden-state metadata
- inspect sheet protection metadata

Agent 2 must NOT on non-Template sheets:

- write values
- clear values
- modify formulas
- rename sheets
- change sheet order
- unhide sheets in the saved workbook
- hide sheets
- change visibility state
- change formatting
- change row heights
- change column widths
- modify validations
- modify named ranges
- modify protection
- insert rows
- delete rows
- insert columns
- delete columns
- merge/unmerge cells
- alter print settings
- alter filters
- alter freeze panes
- alter comments/notes
- alter hyperlinks
- alter any workbook-owned metadata belonging to those sheets

Non-Template sheets are for reading and analysis only.

## 113. Template-Only Write Rule

Agent 2 may modify only intended product-entry cells on the `Template` sheet.

Configured row boundary:

- Rows 1–6: READ-ONLY
- Row 6: usually Amazon example/reference product row
- Product entry starts at row 7
- Rows 7 onward: writable only where the template defines valid product-input cells

Agent 2 must not modify Template cells outside the intended product-entry region.

If a formula, locked cell, system field, lookup cell or non-input region exists on Template:

do not write to it.

Allowed write scope:

`Template!<valid product input cells from row 7 downward>`

Everything else is read-only.

## 114. Non-Destructive Structural Analysis

Agent 2 must analyze hidden columns, grouped columns, hidden rows and workbook structures without permanently changing workbook state.

Preferred method:

- read hidden/grouping metadata programmatically
- inspect hidden columns/rows directly
- read values without unhide operations
- preserve visibility state exactly

Do not unhide other sheets or alter their visibility merely for inspection.

On the Template sheet, if analysis requires logical expansion, perform it in memory or in a temporary analysis copy, not in the final source workbook.

Final workbook must preserve original structure except for intended product values inserted into Template rows 7+.

## 115. Worksheet Integrity Check

Before finalizing the feed, compare all non-Template sheets byte/logical structure where practical.

Verify that there were no unintended changes to:

- values
- formulas
- styles
- dimensions
- validations
- named ranges
- visibility
- protection
- merged cells
- metadata

If any non-Template sheet changed:

`NON_TEMPLATE_SHEET_MODIFIED`

The feed must be blocked.

For Template verify:

- rows 1–6 unchanged
- row 6 unchanged
- only approved rows 7+ changed
- only approved input cells changed
- no unintended formulas/styles/metadata modified

If violation detected:

`TEMPLATE_WRITE_SCOPE_VIOLATION`

## 116. Humanizer + Template Fill Sequence

The write sequence must be:

1. Read Agent 1 canonical data
2. Read and study all relevant non-Template sheets
3. Build schema and mapping
4. Resolve clarifying questions
5. Run dry-run validation
6. Apply Humanizer meaning-preserving cleanup
7. Write values only into Template row 7+
8. Save to a new output file
9. Reopen output file
10. Verify rows 1–6 unchanged
11. Verify all non-Template sheets unchanged
12. Verify only intended Template input cells changed
13. Mark READY_FOR_UPLOAD only if all checks pass

## 117. Final Mutation Policy

Hard rule:

**READ EVERYTHING NEEDED. MODIFY ONLY TEMPLATE PRODUCT CELLS FROM ROW 7 DOWNWARD.**

All other workbook content is immutable.

Any attempt or accidental change outside the permitted write scope is a blocking error.
