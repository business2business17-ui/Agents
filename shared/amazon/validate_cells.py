#!/usr/bin/env python3
"""Dry-run validation of planned cell values against the real template's data validations (no writing).

Usage:
  validate_cells.py --source CLEAN.xlsm --cells cells.json --sheet Template [--min-row 7]
                    [--header-row 5] [--key-column B] [--json OUT.json]

For every planned cell:
  * row >= min-row and the cell is not a formula cell                         (WRITE_SCOPE)
  * the column's machine key (row --header-row) is reported with each finding
  * Excel data validation covering the cell is applied:
      list      -> value must equal an allowed value (inline list, named range or range); case/space-near-misses
                   are reported as ENUM_AMBIGUOUS, never auto-fixed
      whole/decimal/textLength -> operator / bounds
      date/custom/other        -> MANUAL (listed, not guessed)
  * identifier-like columns (sku, external_product_id, ean, upc, gtin, asin, model, part_number...) must be text
  * hidden characters (NBSP, zero-width, control chars, double / edge spaces) and formula-injection prefixes
  * backend search terms byte length (<= 249), generic length warning
  * duplicate values in --key-column across planned rows (DUPLICATE_FEED_ROW)
Exit 0 = no FAIL, 1 = at least one FAIL.
"""
import argparse
import json
import re
import sys
import unicodedata
from decimal import Decimal, InvalidOperation

from xlsx_core import M, Book, col_to_idx, idx_to_col, split_ref

ID_KEYS = re.compile(r"(^|_)(sku|external_product_id|product_id|ean|upc|gtin|asin|isbn|model|model_number|"
                     r"part_number|item_sku|parent_sku|style_number)($|_)", re.I)
HIDDEN = re.compile("[ ​‌‍⁠﻿ \t\r\n\x00-\x08\x0b\x0c\x0e-\x1f]")


def ranges_of(sqref):
    out = []
    for part in sqref.split():
        a, _, b = part.partition(":")
        c1, r1 = split_ref(a)
        c2, r2 = split_ref(b or a)
        out.append((col_to_idx(c1), r1, col_to_idx(c2), r2))
    return out


def in_ranges(ref, rngs):
    c, r = split_ref(ref)
    ci = col_to_idx(c)
    return any(a <= ci <= c_ and r1 <= r <= r2 for a, r1, c_, r2 in rngs)


def range_values(book, ref_text, default_sheet):
    m = re.match(r"^'?([^'!]+)'?!\$?([A-Z]+)\$?(\d+)(?::\$?([A-Z]+)\$?(\d+))?$", ref_text.strip())
    if not m:
        return None
    sheet, c1, r1, c2, r2 = m.groups()
    c2, r2 = c2 or c1, r2 or r1
    try:
        rows = dict(book.rows(sheet, int(r1), int(r2)))
    except KeyError:
        return None
    vals = []
    for r in range(int(r1), int(r2) + 1):
        for ci in range(col_to_idx(c1), col_to_idx(c2) + 1):
            cell = rows.get(r, {}).get(idx_to_col(ci))
            if cell and cell[1] not in (None, ""):
                vals.append(str(cell[1]))
    return vals


def resolve_list(book, formula, sheet):
    f = (formula or "").strip()
    if f.startswith("="):
        f = f[1:]
    if f.startswith('"') and f.endswith('"'):
        return [x for x in f[1:-1].split(",")]
    for dn in book.defined_names:
        if dn["name"] == f:
            return range_values(book, dn["ref"], sheet)
    return range_values(book, f, sheet)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", required=True)
    ap.add_argument("--cells", required=True)
    ap.add_argument("--sheet", required=True)
    ap.add_argument("--min-row", type=int, default=7)
    ap.add_argument("--header-row", type=int, default=5)
    ap.add_argument("--key-column")
    ap.add_argument("--json")
    a = ap.parse_args()

    book = Book(a.source)
    cells = json.load(open(a.cells, encoding="utf-8"))
    root = book.sheet_root(a.sheet)
    headers = {col: v[1] for col, v in dict(book.rows(a.sheet, a.header_row, a.header_row)).get(a.header_row, {}).items()}
    existing = {}
    for r, cs in book.rows(a.sheet, a.min_row, None):
        for col, v in cs.items():
            existing[f"{col}{r}"] = v
    vals = []
    dv = root.find(M + "dataValidations")
    if dv is not None:
        for v in dv:
            f1, f2 = v.find(M + "formula1"), v.find(M + "formula2")
            vals.append(dict(type=v.get("type"), op=v.get("operator") or "between", rngs=ranges_of(v.get("sqref")),
                             f1=f1.text if f1 is not None else None, f2=f2.text if f2 is not None else None,
                             allow_blank=v.get("allowBlank") == "1"))
    findings = []

    def add(sev, ref, code, msg):
        col = split_ref(ref)[0]
        findings.append(dict(severity=sev, cell=ref, field=headers.get(col), code=code, message=msg))

    key_vals = {}
    for c in cells:
        ref = c["cell"].upper()
        col, row = split_ref(ref)
        val, vtype = c.get("value"), c.get("type", "text")
        sval = "" if val is None else str(val)
        if row < a.min_row:
            add("FAIL", ref, "WRITE_SCOPE", f"row {row} < {a.min_row} is read-only")
        if existing.get(ref, ("", ""))[0] == "formula":
            add("FAIL", ref, "WRITE_SCOPE", "target cell holds a formula")
        key = headers.get(col) or ""
        if (ID_KEYS.search(key) or ID_KEYS.search(str(c.get("field", "")))) and vtype != "text":
            add("FAIL", ref, "IDENTIFIER_NOT_TEXT", f"identifier column '{key}' must be written as text (leading zeros)")
        if sval:
            if HIDDEN.search(sval):
                add("FAIL", ref, "HIDDEN_CHARACTER", "contains NBSP / zero-width / control / line-break characters")
            if sval != sval.strip() or "  " in sval:
                add("WARN", ref, "WHITESPACE", "leading/trailing/double spaces")
            if unicodedata.normalize("NFC", sval) != sval:
                add("WARN", ref, "UNICODE_NORMALIZATION", "not NFC-normalised")
            if vtype == "text" and sval.startswith(("=", "+", "-", "@")):
                add("INFO", ref, "FORMULA_PREFIX", "stored as literal text (inline string); verify intended")
            if re.search(r"(search_terms|generic_keyword|keywords)", key, re.I) and len(sval.encode("utf-8")) > 249:
                add("FAIL", ref, "FIELD_LENGTH_EXCEEDED", f"{len(sval.encode('utf-8'))} bytes > 249")
            if len(sval) > 2000:
                add("WARN", ref, "LONG_TEXT", f"{len(sval)} chars; check the template limit")
        for v in vals:
            if not in_ranges(ref, v["rngs"]):
                continue
            if not sval and v["allow_blank"]:
                continue
            t = v["type"]
            if t == "list":
                allowed = resolve_list(book, v["f1"], a.sheet)
                if allowed is None:
                    add("INFO", ref, "VALIDATION_MANUAL", f"list source not resolvable: {v['f1']!r}")
                elif sval not in allowed:
                    near = [x for x in allowed if x.strip().lower() == sval.strip().lower()]
                    if near:
                        add("FAIL", ref, "ENUM_AMBIGUOUS", f"'{sval}' differs only by case/spacing from allowed '{near[0]}': "
                            "ask/approve before using")
                    else:
                        add("FAIL", ref, "ENUM_INVALID", f"'{sval}' not in allowed values ({len(allowed)}): {allowed[:8]}")
            elif t in ("whole", "decimal"):
                try:
                    n = Decimal(sval)
                    if t == "whole" and n != n.to_integral_value():
                        add("FAIL", ref, "DATA_TYPE_ERROR", f"{sval} is not a whole number")
                    lo = Decimal(v["f1"]) if v["f1"] and re.match(r"^-?[\d.]+$", v["f1"]) else None
                    hi = Decimal(v["f2"]) if v["f2"] and re.match(r"^-?[\d.]+$", v["f2"]) else None
                    op = v["op"]
                    bad = ((op == "between" and lo is not None and hi is not None and not lo <= n <= hi) or
                           (op == "greaterThan" and lo is not None and not n > lo) or
                           (op == "greaterThanOrEqual" and lo is not None and not n >= lo) or
                           (op == "lessThan" and lo is not None and not n < lo) or
                           (op == "lessThanOrEqual" and lo is not None and not n <= lo))
                    if bad:
                        add("FAIL", ref, "RANGE_ERROR", f"{sval} violates {op} {v['f1']} {v['f2'] or ''}")
                except InvalidOperation:
                    add("FAIL", ref, "DATA_TYPE_ERROR", f"'{sval}' is not numeric")
            elif t == "textLength":
                n = len(sval)
                lo = int(v["f1"]) if v["f1"] and v["f1"].isdigit() else None
                hi = int(v["f2"]) if v["f2"] and v["f2"].isdigit() else None
                op = v["op"]
                if (op == "between" and lo is not None and hi is not None and not lo <= n <= hi) or \
                   (op == "lessThanOrEqual" and lo is not None and n > lo) or (op == "lessThan" and lo is not None and n >= lo) or \
                   (op == "greaterThanOrEqual" and lo is not None and n < lo):
                    add("FAIL", ref, "FIELD_LENGTH_EXCEEDED", f"length {n} violates {op} {v['f1']} {v['f2'] or ''}")
            else:
                add("INFO", ref, "VALIDATION_MANUAL", f"validation type '{t}' not machine-checked")
        if a.key_column and col == a.key_column.upper() and sval:
            key_vals.setdefault(sval, []).append(ref)
    for k, refs in key_vals.items():
        if len(refs) > 1:
            add("FAIL", refs[0], "DUPLICATE_FEED_ROW", f"value '{k}' appears in {refs}")

    fails = [f for f in findings if f["severity"] == "FAIL"]
    res = dict(source=a.source, sheet=a.sheet, planned_cells=len(cells), fails=len(fails),
               status="FAIL" if fails else "PASS", findings=findings)
    if a.json:
        json.dump(res, open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    for f in findings:
        print(f"  {f['severity']:5} {f['cell']:8} {str(f['field'] or ''):22} {f['code']:22} {f['message']}")
    print(f"DRY RUN: {res['status']} - {len(cells)} planned cells, {len(fails)} FAIL")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
