# GTIN Batch Intake (images named by GTIN + XLSX with TTX and benefits)

Primary input mode for local use (Claude Code). The user drops a folder of product images and one XLSX; the agent does the rest.

## Input contract

1. A repository / working folder.
2. Images whose **file name is the product code**: `GTIN` / `EAN` / `UPC` (`4006381333931.jpg`). Extra angles of the same product: `4006381333931_2.jpg`, `4006381333931-back.png` - the suffix becomes the view label (use it for the "rear view available?" check).
3. An XLSX, **one row per product**, with the same code in a GTIN/EAN/UPC column, the technical characteristics (TTX), and optionally a benefits / advantages column. Column names are free-form (see `universal-xlsx-intake.md`); the GTIN column is found by header or by content.

The image is the protected product layer (`product-fidelity.md`). The XLSX is read-only.

## Step A - match (always first, run the script)

`python scripts/match_inputs.py --images <dir> --xlsx <file> --out creative-studio/out/match.json`

It returns, without guessing: matched products (images + row + facts + benefits + `benefits_status`), `images_without_row`, `rows_without_image`, duplicate rows, invalid / check-digit-failed codes, codes that lost a leading zero in Excel (`ZERO_PADDED`, matched only because the padded code has a valid check digit), non-GTIN file names, image pixel sizes.

Matching treats UPC-12 and EAN-13 with a leading 0 as the same product (GTIN-14 key). Never rename files or edit the XLSX; report instead.

**Blockers worth asking about (one message, recommended answer pre-filled):** duplicate rows for one GTIN; an image without a row (default: skip it, list it); a row without an image (default: plan the row as `DESCRIPTION ONLY - ASSET NOT CREATED`, no production without a source image); an invalid check digit (default: keep the code as typed, flag it, do not fix it). Clean matches proceed without waiting for the broken ones. Re-run the script after the user fixes files.

## Step B - benefits (per product)

| `benefits_status` | What the agent does |
|---|---|
| `PROVIDED` | The user's benefits are the source of truth. Keep their meaning; tighten wording for the visual; claim-check each (`content-improvement.md`). Tag `PROVIDED`. |
| `MISSING_DRAFT_FROM_TTX` | The agent drafts shopper-facing benefits **from the TTX of that row only**. Per benefit: `source fact` -> `shopper meaning` -> `benefit` -> `claim risk`. 3-5 per product, ranked for the carousel. Tag `DRAFTED_FROM_TTX`. |
| `MISSING_NO_TTX` | No facts to build on. Do not write benefits. Blocker: ask for TTX, or plan only MAIN (no marketing copy needed) and list the rest as `NOT READY - missing input`. |

Drafting rules: a benefit may only restate or explain a supplied fact (a 20,000 mAh battery -> "charges a phone several times" only if the arithmetic is explicit and cautious; otherwise state the number). Never add efficacy, health, safety, eco, ranking, certification, "best/premium" or comparative claims that the TTX does not contain. Missing proof -> flag as `NEEDS_PROOF`, do not write it. Units, numbers, models, compatibility are copied exactly. Translation never strengthens a claim.

All `DRAFTED_FROM_TTX` benefits are shown once at checkpoint C1 (next to the fact they come from) and approved in the same `ok`. The user can accept all, or edit by number. After approval they are `APPROVED` in project memory and are never re-asked.

## Step C - plan and production

Per matched product, continue the normal pipeline (carousel strategy, localization, layout, C1). Mapping into the production workbook:

| Data | Workbook column |
|---|---|
| GTIN from the file name / row | `SKU / EAN / GTIN` (as typed, text) |
| image path(s) | `Source Image / File / URL / Drive Link` (real path from `match.json`) |
| row facts | `PRODUCT_TTX` (one line per attribute), `Source TTX / Facts`, `Normalized TTX / Facts` |
| benefits | `CONTENT_INTELLIGENCE` (`Proposed Benefit`, `Proof / Supporting Fact`, `User Approval Status` = `PROVIDED` / `DRAFTED_FROM_TTX` -> `APPROVED`) and `Proposed Benefit` in `ASSET_PLAN` |
| unmatched items | `ISSUES` |

Keep one `Product Row ID` per GTIN so every asset traces back to its image and row. Source quality is checked per image with `scripts/validate_asset.py` (size, aspect, background) before the plan promises anything the file cannot support (for example MAIN fill, or a rear view that only exists as a front photo).

## Scale

Many GTINs: process all clean matches in one plan and one C1; group the table by product. Do not ask per SKU.
