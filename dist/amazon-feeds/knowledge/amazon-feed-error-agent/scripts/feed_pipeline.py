#!/usr/bin/env python3
"""One command for the write path of a feed: validate (dry run) -> patch -> write guard -> verdict.

Usage:
  feed_pipeline.py --source CLEAN.xlsm --cells cells.json --out NEW.xlsm --sheet Template
                   [--min-row 7] [--header-row 5] [--key-column B] [--allow-overwrite] [--report-dir DIR]

Runs the same three tools the agent would run by hand, in the same order, and stops at the first failing step
(a failed dry run never reaches the patcher; nothing is written unless validation passed):
  1. validate_cells.py   -> DIR/validate.json
  2. xlsm_patch.py       -> NEW.xlsm  (+ DIR/patch.json)
  3. workbook_guard.py   -> DIR/guard.json  (--approved = the same cells.json: any unplanned diff fails)
and writes DIR/pipeline.json with the verdict:
  PASS_TO_FULL_AUDIT   all three steps passed; the file still needs the full audit before any READY claim
  NOT_READY            a step failed (see `failed_step` and that step's report); if the failure happened after
                       the patch was written, the output file is removed so a failed feed cannot be uploaded by mistake
Exit 0 = PASS_TO_FULL_AUDIT, 1 = NOT_READY, 2 = usage error.
"""
import argparse
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def run(script, args):
    t = time.time()
    p = subprocess.run([sys.executable, os.path.join(HERE, script)] + args, capture_output=True, text=True)
    return dict(script=script, returncode=p.returncode, seconds=round(time.time() - t, 2),
                stdout_tail=p.stdout.strip().splitlines()[-12:], stderr_tail=p.stderr.strip().splitlines()[-6:])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", required=True)
    ap.add_argument("--cells", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--sheet", required=True)
    ap.add_argument("--min-row", type=int, default=7)
    ap.add_argument("--header-row", type=int, default=5)
    ap.add_argument("--key-column")
    ap.add_argument("--allow-overwrite", action="store_true")
    ap.add_argument("--report-dir")
    a = ap.parse_args()

    rd = a.report_dir or (os.path.splitext(a.out)[0] + "_reports")
    os.makedirs(rd, exist_ok=True)
    rp = lambda n: os.path.join(rd, n)  # noqa: E731
    common = ["--sheet", a.sheet, "--min-row", str(a.min_row)]
    steps, failed = [], None

    v_args = ["--source", a.source, "--cells", a.cells, "--header-row", str(a.header_row), "--json", rp("validate.json")] + common
    if a.key_column:
        v_args += ["--key-column", a.key_column]
    steps.append(dict(name="validate", report=rp("validate.json"), **run("validate_cells.py", v_args)))
    if steps[-1]["returncode"] != 0:
        failed = "validate"
    if not failed:
        p_args = ["--source", a.source, "--cells", a.cells, "--out", a.out, "--report", rp("patch.json")] + common
        if a.allow_overwrite:
            p_args.append("--allow-overwrite")
        steps.append(dict(name="patch", report=rp("patch.json"), **run("xlsm_patch.py", p_args)))
        if steps[-1]["returncode"] != 0:
            failed = "patch"
    if not failed:
        g_args = ["--source", a.source, "--output", a.out, "--approved", a.cells, "--json", rp("guard.json")] + common
        steps.append(dict(name="guard", report=rp("guard.json"), **run("workbook_guard.py", g_args)))
        if steps[-1]["returncode"] != 0:
            failed = "guard"
            if os.path.exists(a.out):
                os.remove(a.out)

    verdict = "NOT_READY" if failed else "PASS_TO_FULL_AUDIT"
    res = dict(verdict=verdict, failed_step=failed, source=a.source, out=None if failed else a.out, steps=steps)
    with open(rp("pipeline.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    for s in steps:
        print(f"{'OK  ' if s['returncode'] == 0 else 'FAIL'} {s['name']:9} {s['seconds']:>6}s  -> {s['report']}")
    if failed:
        print(f"--- {failed} output ---")
        print("\n".join(steps[-1]["stdout_tail"] + steps[-1]["stderr_tail"]))
    print(f"VERDICT: {verdict}" + ("" if failed else "  (full audit still required before READY)"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
