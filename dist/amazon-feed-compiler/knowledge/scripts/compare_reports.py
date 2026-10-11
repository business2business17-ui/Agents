#!/usr/bin/env python3
"""Compare two parsed Processing Reports (output of parse_processing_report.py): re-analysis after a new upload.

Usage:
  compare_reports.py PREVIOUS.json CURRENT.json [--history history.json] [--out result.json]

Tracking key = marketplace + sku + attribute (the original value changes after a fix, so it is not part of the key).
Per previous error: RESOLVED | REJECTED_AGAIN (same code) | CHANGED_ERROR (other code on the same cell) | ESCALATION_REQUIRED
(>= 3 attempts, see --history). New errors in CURRENT start the full cycle. history.json is a dict {key: attempts}
and is updated in --out. Never repeats a fix that already failed: the failed attempts are listed.
"""
import argparse
import json
import sys


def key(f):
    return "|".join(str(f.get(k)) for k in ("marketplace", "sku", "attribute"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("previous")
    ap.add_argument("current")
    ap.add_argument("--history")
    ap.add_argument("--out")
    a = ap.parse_args()
    prev = json.load(open(a.previous, encoding="utf-8"))["findings"]
    cur = json.load(open(a.current, encoding="utf-8"))["findings"]
    hist = json.load(open(a.history, encoding="utf-8")) if a.history else {}
    cur_by = {}
    for f in cur:
        cur_by.setdefault(key(f), []).append(f)
    res, counts = [], dict(RESOLVED=0, REJECTED_AGAIN=0, CHANGED_ERROR=0, ESCALATION_REQUIRED=0, NEW=0)
    seen = set()
    for f in prev:
        if f["severity"] == "UNKNOWN":
            continue
        k = key(f)
        seen.add(k)
        now = cur_by.get(k, [])
        attempts = hist.get(k, 1)
        if not now:
            st = "RESOLVED"
        elif any(x.get("error_code") == f.get("error_code") for x in now):
            st = "REJECTED_AGAIN"
            hist[k] = attempts + 1
        else:
            st = "CHANGED_ERROR"
            hist[k] = attempts + 1
        if st != "RESOLVED" and hist.get(k, attempts) >= 3:
            st = "ESCALATION_REQUIRED"
        counts[st] += 1
        res.append(dict(key=k, status=st, previous_code=f.get("error_code"), current_codes=[x.get("error_code") for x in now],
                        attempts=hist.get(k, attempts), cell=f.get("cell"), attribute=f.get("attribute"), sku=f.get("sku")))
    new = [f for f in cur if key(f) not in seen and f["severity"] != "UNKNOWN"]
    counts["NEW"] = len(new)
    pe = sum(f["severity"] == "ERROR" for f in prev)
    ce = sum(f["severity"] == "ERROR" for f in cur)
    pw = sum(f["severity"] == "WARNING" for f in prev)
    cw = sum(f["severity"] == "WARNING" for f in cur)
    out = dict(previous_errors=pe, current_errors=ce, previous_warnings=pw, current_warnings=cw, counts=counts,
               items=res, new_errors=new, history=hist)
    if a.out:
        json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"Previous errors: {pe} | Resolved: {counts['RESOLVED']} | Remaining: "
          f"{counts['REJECTED_AGAIN'] + counts['CHANGED_ERROR'] + counts['ESCALATION_REQUIRED']} | New: {counts['NEW']}")
    print(f"Warnings: {pw} -> {cw}")
    for r in res:
        if r["status"] != "RESOLVED":
            print(f"  {r['status']:20} {r['key']}  prev={r['previous_code']} now={r['current_codes']} attempts={r['attempts']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
