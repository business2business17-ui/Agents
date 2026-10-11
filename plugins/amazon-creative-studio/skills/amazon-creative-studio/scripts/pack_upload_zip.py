#!/usr/bin/env python3
"""Pack a listing carousel for Seller Central bulk image upload (ZIP).

Usage:
  pack_upload_zip.py --asin B000123456 --main main.jpg --pt pt1.jpg pt2.jpg ... --out DIR [--dry-run] [--force]

Naming (Amazon bulk upload, per the project spec dated 2026-10-11): files `ASIN.MAIN.jpg`, `ASIN.PT01.jpg`,
`ASIN.PT02.jpg` ...; the archive is `ASIN.zip` with the files at its root. One ZIP per ASIN.
Checks before packing: ASIN format, at most 8 PT slots (slot count is VERIFY_IN_UI; this agent plans MAIN + 6),
extension, file exists, size <= 10 MB. Sources are only read (copied into the ZIP under the new names); nothing
is converted, resized or renamed on disk. Exit code 0 = packed / dry-run OK, 1 = refused.
"""
import argparse
import re
import sys
import zipfile
from pathlib import Path

MB = 1024 * 1024
EXT = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}
MAX_PT = 8


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--asin", required=True)
    ap.add_argument("--main", required=True)
    ap.add_argument("--pt", nargs="*", default=[], help="secondary images in carousel order -> PT01, PT02, ...")
    ap.add_argument("--out", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="overwrite an existing ASIN.zip")
    a = ap.parse_args()

    asin = a.asin.strip().upper()
    errors = []
    if not re.fullmatch(r"[A-Z0-9]{10}", asin):
        errors.append(f"ASIN '{a.asin}' must be 10 letters/digits (do not use a GTIN here)")
    if len(a.pt) > MAX_PT:
        errors.append(f"{len(a.pt)} secondary images; at most {MAX_PT} PT slots")
    plan = [("MAIN", Path(a.main))] + [(f"PT{i:02d}", Path(p)) for i, p in enumerate(a.pt, start=1)]
    entries = []
    for slot, src in plan:
        ext = src.suffix.lower()
        if not src.is_file():
            errors.append(f"{slot}: file not found: {src}")
            continue
        if ext not in EXT:
            errors.append(f"{slot}: unsupported extension '{src.suffix}' ({src.name})")
            continue
        if src.stat().st_size > 10 * MB:
            errors.append(f"{slot}: {src.name} is {src.stat().st_size / MB:.1f} MB (max 10 MB)")
            continue
        entries.append((f"{asin}.{slot}{'.jpg' if ext == '.jpeg' else ext}", src))
    zpath = Path(a.out) / f"{asin}.zip"
    if zpath.exists() and not a.force and not a.dry_run:
        errors.append(f"{zpath} exists; use --force to overwrite")
    if errors:
        print("REFUSED:\n  " + "\n  ".join(errors), file=sys.stderr)
        return 1
    for name, src in entries:
        print(f"  {name:28} <- {src}")
    if a.dry_run:
        print(f"dry run OK: would write {zpath}")
        return 0
    zpath.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_STORED) as zf:  # images are already compressed
        for name, src in entries:
            zf.write(src, name)
    print(f"wrote {zpath} ({len(entries)} files, {zpath.stat().st_size / MB:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
