#!/usr/bin/env python3
"""Look up an Amazon feed error code in the structured knowledge base (assets/error_kb.json).

Usage:
  error_kb.py 8541 [8560 ...]            show entries
  error_kb.py --pattern invalid_enum     show a no-code methodology
  error_kb.py --list
Unknown code -> prints UNVERIFIED_CASE and the research checklist (spec section 18). Never auto-fix from here:
this is guidance; the current template + the full error message decide.
"""
import json
import os
import sys

KB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "error_kb.json")


def main():
    kb = json.load(open(KB, encoding="utf-8"))
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if args[0] == "--list":
        for k, v in kb["codes"].items():
            print(f"{k:7} {v['type']:36} auto_fix={v['auto_fix']}  {v['title']}")
        return 0
    if args[0] == "--pattern":
        for p in args[1:]:
            print(p, "->", kb["patterns_without_code"].get(p, "unknown pattern"))
        return 0
    rc = 0
    for code in args:
        e = kb["codes"].get(code)
        if not e:
            rc = 1
            print(f"{code}: UNVERIFIED_CASE - not in the knowledge base. Research order: Feed Processing Summary -> Template -> "
                  "Data Definitions -> Valid Values -> Instructions -> official Amazon docs -> Seller University -> "
                  "Amazon moderators; record source, marketplace, confidence; propose a fix; wait for user approval; "
                  "add to KB only after a successful re-upload (VERIFIED_BY_SUCCESSFUL_REUPLOAD).")
            continue
        print(json.dumps({code: e}, ensure_ascii=False, indent=2))
    return rc


if __name__ == "__main__":
    sys.exit(main())
