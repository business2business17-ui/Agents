#!/usr/bin/env python3
"""Write approved cell values into ONE sheet of an Amazon feed workbook without touching anything else.

Usage:
  xlsm_patch.py --source CLEAN.xlsm --cells cells.json --out NEW.xlsm --sheet Template [--min-row 7]
                [--allow-overwrite] [--dry-run]

cells.json = [ {"cell": "K7", "value": "Blue", "type": "text"},            # text | number | bool
               {"cell": "B7", "value": "0012345678905", "type": "text"},   # identifiers: ALWAYS text
               {"cell": "BK17", "value": "Blue", "expect_old": "Bluee", "change_id": "CHG-001"} ]

How it preserves the workbook: the package is copied entry by entry; only the target sheet part is
re-serialized, and inside it only the touched <c> cells change. Macros (vbaProject.bin), styles,
validations, defined names, hidden state and every other sheet stay byte-identical. Text is stored as
inline strings, so values beginning with = + - @ can never become formulas.

Safety rules enforced here (violations abort with exit 1 and write nothing):
  * target row must be >= --min-row (default 7; rows 1-6 are read-only)
  * the source file is never modified; --out must differ from --source
  * a cell holding a formula is never overwritten
  * an existing non-empty cell is overwritten only with --allow-overwrite or a matching expect_old
  * duplicate target cells are rejected
"""
import argparse
import io
import json
import sys
import zipfile
from decimal import Decimal, InvalidOperation

from lxml import etree

from xlsx_core import M, Book, col_to_idx, idx_to_col, parse_xml, serialize, split_ref

XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
INJECTION_PREFIXES = ("=", "+", "-", "@")


def die(msg):
    print("ABORT:", msg, file=sys.stderr)
    sys.exit(1)


def find_or_create_row(sd, r):
    prev = None
    for row in sd:
        rn = int(row.get("r"))
        if rn == r:
            return row
        if rn > r:
            new = etree.Element(M + "row", r=str(r))
            row.addprevious(new)
            return new
        prev = row
    new = etree.SubElement(sd, M + "row", r=str(r))
    return new


def find_or_create_cell(row, ref):
    col, _ = split_ref(ref)
    ci = col_to_idx(col)
    for c in row:
        cc, _ = split_ref(c.get("r"))
        if cc == col:
            return c, False
        if col_to_idx(cc) > ci:
            new = etree.Element(M + "c", r=ref)
            c.addprevious(new)
            return new, True
    return etree.SubElement(row, M + "c", r=ref), True


def set_value(c, value, vtype):
    for ch in list(c):
        c.remove(ch)
    if "t" in c.attrib:
        del c.attrib["t"]
    if value is None or value == "":
        return "empty"
    if vtype == "number":
        try:
            d = Decimal(str(value))
        except InvalidOperation:
            die(f"{c.get('r')}: not a number: {value!r}")
        etree.SubElement(c, M + "v").text = format(d, "f")
        return "number"
    if vtype == "bool":
        c.set("t", "b")
        etree.SubElement(c, M + "v").text = "1" if str(value).lower() in ("1", "true", "yes") else "0"
        return "bool"
    c.set("t", "inlineStr")
    is_ = etree.SubElement(c, M + "is")
    t = etree.SubElement(is_, M + "t")
    t.text = str(value)
    t.set(XML_SPACE, "preserve")
    return "text"


def update_dimension(root, touched_refs):
    dim = root.find(M + "dimension")
    if dim is None or ":" not in (dim.get("ref") or ""):
        return
    a, b = dim.get("ref").split(":")
    (c1, r1), (c2, r2) = split_ref(a), split_ref(b)
    for ref in touched_refs:
        c, r = split_ref(ref)
        c1, c2 = (c if col_to_idx(c) < col_to_idx(c1) else c1), (c if col_to_idx(c) > col_to_idx(c2) else c2)
        r1, r2 = min(r1, r), max(r2, r)
    dim.set("ref", f"{c1}{r1}:{c2}{r2}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", required=True)
    ap.add_argument("--cells", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--sheet", required=True)
    ap.add_argument("--min-row", type=int, default=7)
    ap.add_argument("--allow-overwrite", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--report")
    a = ap.parse_args()

    if a.out == a.source:
        die("--out must differ from --source (the clean source feed is read-only)")
    with open(a.cells, encoding="utf-8") as f:
        cells = json.load(f)
    seen = set()
    for c in cells:
        col, row = split_ref(c["cell"])
        if row < a.min_row:
            die(f"{c['cell']}: row {row} < {a.min_row}; rows 1-{a.min_row - 1} are READ-ONLY")
        if c["cell"].upper() in seen:
            die(f"duplicate target cell {c['cell']}")
        seen.add(c["cell"].upper())

    book = Book(a.source)
    part = book.sheet_part(a.sheet)
    root = parse_xml(book.entries[part])
    sd = root.find(M + "sheetData")
    report, touched = [], []
    for c in cells:
        ref = c["cell"].upper()
        _, rn = split_ref(ref)
        row = find_or_create_row(sd, rn)
        if "spans" in row.attrib:
            del row.attrib["spans"]
        cell, created = find_or_create_cell(row, ref)
        old_kind, old_val = book.cell_value(cell) if not created else ("empty", None)
        if old_kind == "formula":
            die(f"{ref}: cell contains a formula; never overwritten")
        if old_kind != "empty":
            ok = a.allow_overwrite or ("expect_old" in c and str(c["expect_old"]) == str(old_val))
            if not ok:
                die(f"{ref}: cell not empty (current {old_val!r}); needs expect_old or --allow-overwrite")
        elif "expect_old" in c and c["expect_old"] not in (None, ""):
            die(f"{ref}: expect_old {c['expect_old']!r} but cell is empty")
        vtype = c.get("type", "text")
        val = c.get("value")
        injected = vtype == "text" and isinstance(val, str) and val.startswith(INJECTION_PREFIXES)
        kind = set_value(cell, val, vtype)
        touched.append(ref)
        report.append(dict(cell=ref, old=old_val, new=val, type=kind, change_id=c.get("change_id"),
                           formula_injection_neutralized=injected))
    update_dimension(root, touched)

    summary = dict(source=a.source, out=a.out, sheet=a.sheet, part=part, cells_written=len(report),
                   min_row=a.min_row, macros_preserved=book.has_macros, changes=report)
    if a.dry_run:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        print("DRY RUN: nothing written")
        return 0

    new_part = serialize(root)
    buf = io.BytesIO()
    with zipfile.ZipFile(a.source) as zin, zipfile.ZipFile(buf, "w") as zout:
        for zi in zin.infolist():
            data = new_part if zi.filename == part else zin.read(zi.filename)
            ni = zipfile.ZipInfo(zi.filename, date_time=zi.date_time)
            ni.compress_type = zi.compress_type
            ni.external_attr = zi.external_attr
            ni.comment = zi.comment
            zout.writestr(ni, data)
    with open(a.out, "wb") as f:
        f.write(buf.getvalue())
    if a.report:
        with open(a.report, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"wrote {a.out}: {len(report)} cells in '{a.sheet}' (rows >= {a.min_row}); "
          f"all other package parts byte-identical")
    return 0


if __name__ == "__main__":
    sys.exit(main())
