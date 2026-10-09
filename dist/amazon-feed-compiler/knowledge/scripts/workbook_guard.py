#!/usr/bin/env python3
"""Compare a SOURCE feed with an OUTPUT feed and prove that only approved Template cells changed.

Usage:
  workbook_guard.py --source CLEAN.xlsm --output NEW.xlsm --sheet Template [--min-row 7]
                    [--approved cells.json] [--json OUT.json]

Checks (each PASS / FAIL):
  package_parts        same set of package parts; every non-target part byte-identical
                       (covers other sheets, macros, styles, validations of other sheets, defined names)
  workbook_xml         workbook.xml (sheet order, names, visibility, defined names) identical
  sheet_structure      target sheet XML outside <sheetData>/<dimension> identical
                       (validations, merged cells, columns, protection, conditional formatting, panes)
  rows_below_min_row   every row < min-row identical (rows 1-6 read-only)
  existing_rows        no row/cell at >= min-row removed or restyled without being changed by value
  changed_cells        every changed cell is listed in --approved with the same value (no unauthorized diff)
  approved_applied     every approved change is present with the approved value and type (text stays text)
  formulas             no formula cell changed or added
  injection            no text cell starting with = + - @ is stored as a formula
Exit 0 = all PASS (file may be considered for READY), 1 = at least one FAIL.
"""
import argparse
import json
import sys

from lxml import etree

from xlsx_core import M, Book, parse_xml, sha256, split_ref


def canon(el):
    return etree.tostring(el, method="c14n")


def cell_map(book, root):
    sd = root.find(M + "sheetData")
    out, styles = {}, {}
    for row in sd:
        for c in row:
            ref = c.get("r")
            out[ref] = book.cell_value(c)
            styles[ref] = c.get("s")
    return out, styles, {int(r.get("r")): r for r in sd}


def strip_data(root):
    clone = etree.fromstring(etree.tostring(root))
    for tag in ("sheetData", "dimension"):
        el = clone.find(M + tag)
        if el is not None:
            clone.remove(el)
    return canon(clone)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--sheet", required=True)
    ap.add_argument("--min-row", type=int, default=7)
    ap.add_argument("--approved")
    ap.add_argument("--json")
    a = ap.parse_args()

    src, out = Book(a.source), Book(a.output)
    checks = []

    def chk(name, ok, detail):
        checks.append(dict(check=name, status="PASS" if ok else "FAIL", detail=detail))

    part = src.sheet_part(a.sheet)
    # 1. package parts
    s_names, o_names = set(src.entries), set(out.entries)
    diff_parts = sorted(n for n in s_names & o_names if n != part and src.entries[n] != out.entries[n])
    chk("package_parts", s_names == o_names and not diff_parts,
        f"missing={sorted(s_names - o_names)} extra={sorted(o_names - s_names)} changed_non_target={diff_parts}"
        if (s_names != o_names or diff_parts) else
        f"{len(s_names)} parts; all except '{part}' byte-identical (macros={'yes' if src.has_macros else 'no'})")
    chk("workbook_xml", src.entries["xl/workbook.xml"] == out.entries["xl/workbook.xml"],
        "sheet order/names/visibility/defined names identical" if src.entries["xl/workbook.xml"] == out.entries["xl/workbook.xml"]
        else "xl/workbook.xml differs")

    s_root, o_root = parse_xml(src.entries[part]), parse_xml(out.entries[part])
    chk("sheet_structure", strip_data(s_root) == strip_data(o_root),
        "validations, merges, columns, protection, conditional formatting, panes identical"
        if strip_data(s_root) == strip_data(o_root) else "target sheet XML differs outside sheetData")

    s_cells, s_styles, s_rows = cell_map(src, s_root)
    o_cells, o_styles, o_rows = cell_map(out, o_root)

    # 3. rows below min-row
    bad_low = []
    for rn, row in s_rows.items():
        if rn < a.min_row:
            o = o_rows.get(rn)
            if o is None or canon(row) != canon(o):
                bad_low.append(rn)
    for rn in o_rows:
        if rn < a.min_row and rn not in s_rows and len(o_rows[rn]):
            bad_low.append(rn)
    chk("rows_below_min_row", not bad_low,
        f"rows {sorted(set(bad_low))} differ" if bad_low else f"rows 1-{a.min_row - 1} identical")

    # 4. changed cells
    changed = []
    for ref in sorted(set(s_cells) | set(o_cells), key=lambda r: (split_ref(r)[1], split_ref(r)[0])):
        sv, ov = s_cells.get(ref, ("empty", None)), o_cells.get(ref, ("empty", None))
        if sv != ov or s_styles.get(ref) != o_styles.get(ref):
            changed.append((ref, sv, ov, s_styles.get(ref) != o_styles.get(ref)))
    restyled = [c[0] for c in changed if c[3]]
    chk("existing_rows", not restyled, f"style changed on {restyled[:20]}" if restyled else "no style changes")
    low = [c[0] for c in changed if split_ref(c[0])[1] < a.min_row]
    chk("no_write_below_min_row", not low, f"cells changed in protected rows: {low}" if low else "none")
    f_changed = [c[0] for c in changed if "formula" in (c[1][0], c[2][0])]
    chk("formulas", not f_changed, f"formula cells changed/added: {f_changed}" if f_changed else "no formula touched")
    inj = [ref for ref, (k, v) in o_cells.items()
           if k == "formula" and ref in {c[0] for c in changed}]
    chk("injection", not inj, f"changed cells stored as formulas: {inj}" if inj else
        "no changed cell is a formula; text beginning with = + - @ is stored as text")

    # 5. approved list
    if a.approved:
        with open(a.approved, encoding="utf-8") as f:
            approved = {c["cell"].upper(): c for c in json.load(f)}
        unauthorized = [c[0] for c in changed if c[0] not in approved]
        chk("changed_cells", not unauthorized,
            f"UNAUTHORIZED DIFF in {unauthorized[:30]}" if unauthorized else
            f"{len(changed)} changed cells, all approved")
        problems = []
        for ref, c in approved.items():
            kind, val = o_cells.get(ref, ("empty", None))
            want_type = c.get("type", "text")
            want = c.get("value")
            if want in (None, ""):
                if kind != "empty":
                    problems.append(f"{ref}: expected empty, got {val!r}")
                continue
            if want_type == "text":
                if kind != "text" or val != str(want):
                    problems.append(f"{ref}: expected text {want!r}, got {kind} {val!r}")
            elif want_type == "number":
                try:
                    from decimal import Decimal
                    ok = kind == "number" and Decimal(str(val)) == Decimal(str(want))
                except Exception:  # noqa: BLE001
                    ok = False
                if not ok:
                    problems.append(f"{ref}: expected number {want}, got {kind} {val!r}")
            elif want_type == "bool":
                if kind != "bool":
                    problems.append(f"{ref}: expected bool, got {kind}")
        chk("approved_applied", not problems,
            "; ".join(problems[:15]) if problems else f"{len(approved)}/{len(approved)} approved changes applied exactly "
            "(identifiers kept as text)")
    else:
        checks.append(dict(check="changed_cells", status="MANUAL",
                           detail=f"{len(changed)} cells changed; pass --approved to prove each is authorised: "
                                  f"{[c[0] for c in changed][:20]}"))

    overall = "FAIL" if any(c["status"] == "FAIL" for c in checks) else "PASS"
    res = dict(source=a.source, output=a.output, sheet=a.sheet, min_row=a.min_row, overall=overall,
               changed_cells=[c[0] for c in changed], checks=checks)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
    for c in checks:
        print(f"  {c['status']:6} {c['check']:22} {c['detail']}")
    print(f"WRITE GUARD: {overall}  ({'file may proceed to full audit' if overall == 'PASS' else 'NOT READY FOR AMAZON UPLOAD'})")
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
