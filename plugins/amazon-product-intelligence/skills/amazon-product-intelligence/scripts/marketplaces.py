#!/usr/bin/env python3
"""Amazon marketplace table: domain, currency, content languages (see marketplaces.json).

Usage:
  marketplaces.py --list
  marketplaces.py DE [CA ...]        show domain, currency, languages, whether the language must be chosen per listing
  marketplaces.py DE --language de   exit 0 if 'de' is a known content language of DE, 1 otherwise
Import: from marketplaces import info, languages, currency, needs_language_choice
The table is general knowledge, not verified against the seller's account: confirm languages in Seller Central / the feed template.
"""
import json
import os
import sys

_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "marketplaces.json")
_DATA = json.load(open(_PATH, encoding="utf-8"))


def norm(code):
    c = (code or "").strip().upper()
    return _DATA.get("aliases", {}).get(c, c)


def info(code):
    return _DATA["marketplaces"].get(norm(code))


def languages(code):
    i = info(code)
    return list(i["languages"]) if i else []


def currency(code):
    i = info(code)
    return i["currency"] if i else None


def needs_language_choice(code):
    i = info(code)
    return bool(i and (i.get("multi_language") or len(i["languages"]) > 1))


def main():
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if a[0] == "--list":
        for k, v in _DATA["marketplaces"].items():
            print(f"{k:3} {v['domain']:16} {v['currency']}  languages={','.join(v['languages'])}{'  (choose per listing)' if v.get('multi_language') else ''}")
        return 0
    codes = [x for x in a if not x.startswith("--") and (a.index(x) == 0 or a[a.index(x) - 1] != "--language")]
    lang = a[a.index("--language") + 1].lower() if "--language" in a else None
    rc = 0
    for c in codes:
        i = info(c)
        if not i:
            print(f"{c}: unknown marketplace code (add it to marketplaces.json after checking the seller account)")
            rc = 1
            continue
        print(f"{norm(c)}: {i['domain']} {i['currency']} languages={i['languages']} choose_language_per_listing={needs_language_choice(c)} {i.get('note', '')}")
        if lang and lang not in i["languages"]:
            print(f"  language '{lang}' is not in the table for {norm(c)}: VERIFY_IN_UI")
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
