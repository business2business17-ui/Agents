# Processing Summary - current Seller Central layout and worked cases

## Layout (US reports seen so far; other marketplaces: confirm with the file)
- Sheet `Feed Processing Summary`: counters (`Number of SKUs processed / successful / successful with other errors / unsuccessful due to errors / with warnings`), then **two tables**:
  1. *Errors and Warnings per Error Code*: `# | Error code | Category of error | Store | Error message | Affected field (Impacted column) | Number of errors`;
  2. *Errors and Warnings per SKU*: `# | Error code | Category | Store | Error message | Affected field (Impacted cell) | SKU`.
- Sheet `Template`: three **leading status columns** are added (`::submission_status` = `SUCCESS` / `SUCCESS (OTHER ERROR)`, `::number_of_attributes_with_errors`, `::number_of_attributes_with_other_suggestions`). Every cell letter in the report is therefore 3 columns to the right of the same attribute in the uploaded feed.
- "Impacted cell" (e.g. `B35`) is the **status cell of that row**, not the faulty attribute. The attribute is derived: a media URL named in the message is searched in the row; "Your generic_keyword contains ..." names the attribute; otherwise the finding stays row-level (`attribute: null`).
- Row 1 `settings=feedType=...&timestamp=...` carries the upload timestamp: use it to order reports. Two reports with the same timestamp are one upload (`SAME_REPORT`).

## Procedure
1. `parse_processing_report.py REPORT.xlsm --marketplace US --json parsed.json` - groups (code, SKUs, attributes), status counts, reported totals, `depends_on_codes`.
2. `build_change_plan.py parsed.json --feed ORIGINAL.xlsm --out plan.json` - locates every fix by **SKU + attribute key in the original feed** (never by the report's letters); `CELL_CHANGE` items with current/proposed values; `ACTION_ONLY` groups for errors a cell edit cannot fix; `ORIGINAL_DIFFERS` when the file in hand is not the file that was uploaded.
3. Checkpoint C1 (one message): groups with counts, cell changes with Before/After, actions, consequence errors, what the user must decide.
4. After approval: `build_change_plan.py ... --approve ALL|CHG-001,... --cells-out cells.json`, then `xlsm_patch.py` and `workbook_guard.py` (unchanged).
5. After the next upload: `compare_reports.py previous.json current.json` (order by timestamp; prints `TRANSIENT_HINT` for media errors that hit different URLs each time).

## Worked cases (user's US account, 2026-09/10; examples, not rules)
| Case | Report facts | Reading | Action |
|---|---|---|---|
| Phone cases, 1639 SKUs, upload 2026-09-30 ("UPDATED" file) | 0 successful, 1639 "successful with other errors": 100730 on 1628 SKUs (identical listing already processing), 13013 on 1627 (offer without catalog item), 18299 on 11 (brand approval), 20000 on 27, 300060 on 28 | 100730 = the same feed was submitted again while the first was still processing; 13013 is a consequence | Do not edit cells. Wait for the first processing, read the report of the first upload; brand approval for the 11 SKUs; media per below |
| Same feed, upload 2026-10-06 | 1607 successful, 32 SKUs with 36 timeouts (code 20000) only | The duplicate/consequence errors are gone. Different URLs time out each run, from one host (`content.uvmaster.ru`) | No cell change: wait 15-20 min and resubmit only the 32 SKUs (partial update); long term: faster/reliable media hosting |
| AirPods cases, 130 SKUs, upload 2026-10-11 | 62 successful, 68 with errors: 5561 on 65 SKUs (`PROCASE` in `generic_keyword`), 13013 on the same 65, 20000 on 3 | 5561 blocks item creation; 13013 is its consequence | One deterministic fix: remove the flagged term from `generic_keyword` (term occurs nowhere else in the feed), approve, patch, guard PASS (65/65), re-upload; media as above |

Rules that follow: a regression between two reports is first compared by timestamp and by error codes (duplicate submission looks like a disaster but is not a content problem); consequence codes are never "fixed" directly; transient media errors are not solved by editing the file.
