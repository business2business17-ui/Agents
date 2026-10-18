#!/usr/bin/env python3
"""Read-only structural inspection of an Amazon feed workbook (.xlsx/.xlsm). Never modifies the file.

Usage:
  xlsm_inspect.py FEED.xlsm [--sheet Template] [--rows 8] [--json OUT.json]

Reports: file hash, macros, every sheet (visibility, dimension, hidden rows/columns, merged cells,
data validations, protection, conditional formatting), defined names, template-sheet candidates,
rows 1..N of the template sheet with cell references (headers, machine keys, example row, first
data row), data-start check, and fingerprint hashes (header / validation / structure).
"""
import argparse
import json
import sys

from xlsx_core import M, TEMPLATE_NAME_HINTS, Book, sha256


def sheet_info(book, s):
    info = dict(name=s["name"], state=s["state"], part=s["part"])
    root = book.sheet_root(s["name"])
    dim = root.find(M + "dimension")
    info["dimension"] = dim.get("ref") if dim is not None else None
    sd = root.find(M + "sheetData")
    info["rows_in_xml"] = len(sd)
    info["hidden_rows"] = sorted(int(r.get("r")) for r in sd if r.get("hidden") == "1")[:200]
    info["grouped_rows"] = sorted(int(r.get("r")) for r in sd if r.get("outlineLevel"))[:200]
    cols = root.find(M + "cols")
    hidden_cols, grouped_cols = [], []
    if cols is not None:
        for c in cols:
            rng = (int(c.get("min")), int(c.get("max")))
            if c.get("hidden") == "1":
                hidden_cols.append(rng)
            if c.get("outlineLevel"):
                grouped_cols.append(rng)
    info["hidden_col_ranges"] = hidden_cols
    info["grouped_col_ranges"] = grouped_cols
    mc = root.find(M + "mergeCells")
    info["merged_cells"] = len(mc) if mc is not None else 0
    dv = root.find(M + "dataValidations")
    vals = []
    if dv is not None:
        for v in dv:
            f1 = v.find(M + "formula1")
            vals.append(dict(type=v.get("type"), sqref=v.get("sqref"), operator=v.get("operator"),
                             formula1=(f1.text[:160] if f1 is not None and f1.text else None)))
    info["data_validations"] = len(vals)
    info["data_validation_samples"] = vals[:15]
    info["protected"] = root.find(M + "sheetProtection") is not None
    info["conditional_formatting"] = len(root.findall(M + "conditionalFormatting"))
    pane = root.find(f"{M}sheetViews/{M}sheetView/{M}pane")
    info["freeze_panes"] = pane.get("topLeftCell") if pane is not None else None
    info["has_formulas"] = any(c.find(M + "f") is not None for r in sd for c in r)
    return info, root


def validation_hash(root):
    dv = root.find(M + "dataValidations")
    if dv is None:
        return sha256(b"")
    from lxml import etree
    return sha256(etree.tostring(dv, method="c14n"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--sheet", help="name of the data-entry sheet (default: auto-detect)")
    ap.add_argument("--rows", type=int, default=8, help="dump rows 1..N of the template sheet")
    ap.add_argument("--json")
    a = ap.parse_args()

    with open(a.file, "rb") as f:
        raw = f.read()
    book = Book(a.file)
    out = dict(file=a.file, size=len(raw), sha256=sha256(raw),
               kind="xlsm" if book.has_macros or a.file.lower().endswith(".xlsm") else "xlsx",
               macros_present=book.has_macros, sheets=[], defined_names=book.defined_names[:200])
    roots = {}
    for s in book.sheets:
        info, root = sheet_info(book, s)
        roots[s["name"]] = root
        out["sheets"].append(info)

    cands = [s["name"] for s in book.sheets if TEMPLATE_NAME_HINTS.match(s["name"])]
    if not cands:  # fall back: widest sheet with a dense header block
        scored = []
        for s in book.sheets:
            widest = max((len(c) for _, c in book.rows(s["name"], 1, 6)), default=0)
            scored.append((widest, s["name"]))
        scored.sort(reverse=True)
        cands = [n for w, n in scored[:2] if w > 5]
    out["template_candidates"] = cands
    sheet = a.sheet or (cands[0] if cands else None)
    out["template_sheet"] = sheet
    out["template_sheet_confirmed_by_user"] = bool(a.sheet)

    if sheet:
        dump = []
        for r, cells in book.rows(sheet, 1, a.rows):
            dump.append(dict(row=r, cells={c: v[1] if v[0] != "formula" else "=" + v[1] for c, v in cells.items()},
                             kinds={c: v[0] for c, v in cells.items()}))
        out["template_rows"] = dump
        by_row = {d["row"]: d for d in dump}
        n_cells = {r: len(d["cells"]) for r, d in by_row.items()}
        out["row_cell_counts"] = n_cells
        row7 = by_row.get(7)
        out["data_start_check"] = dict(
            expected_first_data_row=7,
            row6_has_content=6 in by_row,
            row7_empty=row7 is None,
            status="DATA_START_CONFIRMED" if (6 in by_row and row7 is None) else "TEMPLATE_ROW7_CONFLICT",
            note=("row 7 is empty and row 6 has content (Amazon example row): consistent with the configured "
                  "boundary" if (6 in by_row and row7 is None) else
                  "row 7 already has content or row 6 is empty: STOP, do not write, ask the user"),
        )
        hdr = [d for d in dump if d["row"] <= 6]
        header_blob = json.dumps([[d["row"], d["cells"]] for d in hdr if d["row"] != 6], sort_keys=True,
                                 ensure_ascii=False).encode()
        root = roots[sheet]
        part = book.sheet_part(sheet)
        out["fingerprint"] = dict(
            template_file_sha256=out["sha256"],
            header_hash=sha256(header_blob),
            validation_hash=validation_hash(root),
            sheet_structure_hash=sha256(("|".join(f"{s['name']}:{s['state']}" for s in book.sheets)).encode()),
            template_part=part,
        )

    text = json.dumps(out, ensure_ascii=False, indent=2, default=str)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print(f"wrote {a.json}")
    print(f"{a.file}: {out['kind']}, macros={out['macros_present']}, sheets={[s['name'] + '(' + s['state'] + ')' for s in out['sheets']]}")
    print(f"template sheet: {sheet} (candidates {cands})")
    if sheet:
        print("data start:", out["data_start_check"]["status"], "-", out["data_start_check"]["note"])
        print("validations on template:", next(s['data_validations'] for s in out['sheets'] if s['name'] == sheet))
    if not a.json:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
