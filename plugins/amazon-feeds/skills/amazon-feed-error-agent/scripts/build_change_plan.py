#!/usr/bin/env python3
"""Turn a parsed Processing Report into a Change Plan against the ORIGINAL feed (read-only), and write approved cells for xlsm_patch.

Usage:
  build_change_plan.py parsed.json --feed ORIGINAL.xlsm --out change_plan.json [--sheet Template] [--header-row 5] [--min-row 7]
                       [--approve ALL|CHG-001,CHG-004] [--cells-out cells.json]

Why against the original feed: the downloaded Processing Report workbook has 3 leading status columns, so its cell letters differ
from the uploaded feed. Every finding is therefore located by SKU (row) + attribute key (header row 5) in the feed you will patch.

Plan items
  CELL_CHANGE   a deterministic cell fix exists (e.g. remove a flagged trademark term from generic_keyword): current, proposed,
                error_code, reason, confidence. Written to cells.json (with expect_old + change_id) ONLY for approved ids.
  ACTION_ONLY   no cell edit helps (media timeouts, duplicate in processing, brand approval, consequence errors): grouped, with the
                recommended action from assets/error_kb.json. They are never turned into cell edits.
  ORIGINAL_DIFFERS / SKU_NOT_IN_FEED  the feed in hand does not match the report: nothing is proposed for it.
Nothing here edits a feed. Approval is explicit (--approve); without it cells.json is not written.
"""
import argparse
import json
import os
import re
import sys
from collections import defaultdict

from xlsx_core import Book, TEMPLATE_NAME_HINTS

KB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "error_kb.json")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("parsed")
    ap.add_argument("--feed", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--sheet")
    ap.add_argument("--header-row", type=int, default=5)
    ap.add_argument("--min-row", type=int, default=7)
    ap.add_argument("--approve", default="")
    ap.add_argument("--cells-out")
    a = ap.parse_args()

    parsed = json.load(open(a.parsed, encoding="utf-8"))
    kb = json.load(open(KB, encoding="utf-8"))["codes"]
    book = Book(a.feed)
    sheet = a.sheet or next((s["name"] for s in book.sheets if TEMPLATE_NAME_HINTS.match(s["name"])), None)
    if not sheet:
        sys.exit("cannot identify the data sheet; pass --sheet")
    hdr = {c: str(v[1]) for c, v in dict(book.rows(sheet, a.header_row, a.header_row)).get(a.header_row, {}).items()}
    by_key = {k: c for c, k in hdr.items()}
    sku_col = by_key.get("contribution_sku#1.value") or next((c for c, k in hdr.items() if re.search(r"sku", k, re.I)), None)
    rows = {r: {c: v[1] for c, v in cells.items()} for r, cells in book.rows(sheet, a.min_row)}
    sku_row = {}
    for r, vals in rows.items():
        if sku_col and vals.get(sku_col) is not None:
            sku_row.setdefault(str(vals[sku_col]).strip(), r)

    items, actions, n = [], defaultdict(lambda: dict(skus=set(), count=0)), 0
    for f in parsed["findings"]:
        code = str(f.get("error_code"))
        if f.get("proposed_value") is not None and f.get("attribute") and f.get("sku"):
            r = sku_row.get(f["sku"])
            col = by_key.get(f["attribute"])
            if r is None or col is None:
                items.append(dict(kind="SKU_NOT_IN_FEED" if r is None else "ATTRIBUTE_NOT_IN_FEED", sku=f["sku"], attribute=f["attribute"], error_code=code))
                continue
            cur = rows[r].get(col)
            if str(cur) != str(f.get("original_value")):
                items.append(dict(kind="ORIGINAL_DIFFERS", sku=f["sku"], cell=f"{col}{r}", attribute=f["attribute"], error_code=code,
                                  in_feed=cur, in_report=f.get("original_value"),
                                  note="the feed in hand is not the file that was uploaded: nothing proposed"))
                continue
            n += 1
            items.append(dict(kind="CELL_CHANGE", change_id=f"CHG-{n:03d}", sku=f["sku"], row=r, cell=f"{col}{r}", attribute=f["attribute"],
                              current=cur, proposed=f["proposed_value"], error_code=code, reason=f.get("proposed_how") or kb.get(code, {}).get("title"),
                              source="Processing Report message + error_kb", confidence=f.get("confidence") or "MEDIUM", user_decision="PENDING"))
        else:
            g = actions[code]
            g["count"] += 1
            if f.get("sku"):
                g["skus"].add(f["sku"])
            g.setdefault("attributes", set())
            if f.get("attribute"):
                g["attributes"].add(f["attribute"].split("[")[0])
    codes_by_sku = defaultdict(set)
    for f in parsed["findings"]:
        if f.get("sku"):
            codes_by_sku[f["sku"]].add(str(f.get("error_code")))
    action_items = []
    for code, g in sorted(actions.items(), key=lambda kv: -kv[1]["count"]):
        e = kb.get(code, {})
        action_items.append(dict(kind="ACTION_ONLY", error_code=code, title=e.get("title", "UNVERIFIED_CASE: research (error_kb.py)"), errors=g["count"],
                                 skus=len(g["skus"]), sku_examples=sorted(g["skus"])[:5], attributes=sorted(g["attributes"]),
                                 depends_on=e.get("depends_on", []),
                                 co_occurring_codes=sorted({c for k in g["skus"] for c in codes_by_sku[k]} - {code}),
                                 diagnose=e.get("diagnose"), recommended=e.get("solution"),
                                 auto_fix=False))
    approve = {x.strip() for x in a.approve.split(",") if x.strip()}
    cells = []
    for it in items:
        if it["kind"] == "CELL_CHANGE" and ("ALL" in approve or it["change_id"] in approve):
            it["user_decision"] = "APPROVED"
            cells.append(dict(cell=it["cell"], value=it["proposed"], type="text", expect_old=it["current"], change_id=it["change_id"]))
    plan = dict(source_report=os.path.basename(parsed.get("file", "")), feed=os.path.basename(a.feed), sheet=sheet, items=items + action_items,
                summary=dict(cell_changes=sum(i["kind"] == "CELL_CHANGE" for i in items), approved=len(cells),
                             mismatches=sum(i["kind"] in ("ORIGINAL_DIFFERS", "SKU_NOT_IN_FEED", "ATTRIBUTE_NOT_IN_FEED") for i in items),
                             action_groups=len(action_items)))
    json.dump(plan, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2, default=str)
    if cells:
        json.dump(cells, open(a.cells_out or os.path.splitext(a.out)[0] + "_cells.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"plan: {plan['summary']}")
    for g in action_items:
        print(f"  ACTION_ONLY code {g['error_code']:7} {g['errors']:5} errors / {g['skus']:5} SKUs  {g['title']}"
              f"{'  [consequence: fix first ' + ','.join(g['co_occurring_codes']) + ']' if g['depends_on'] and g['co_occurring_codes'] else ''}")
    return 0 if not plan["summary"]["mismatches"] else 1


if __name__ == "__main__":
    sys.exit(main())
