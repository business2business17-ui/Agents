#!/usr/bin/env python3
"""Parse the Processing Report that Amazon writes into a feed workbook (read-only).

Usage:
  parse_processing_report.py FEED.xlsm --marketplace DE [--sheet Template] [--header-row 5] [--min-row 7]
                             [--sku-key item_sku] [--json OUT.json]

Extracts
  1. the summary table ("Errors and Warnings per Error Code": code, category, message, affected field,
     impacted column, number of errors) from whichever sheet holds it (EN/DE/FR/IT/ES/RU header synonyms);
  2. Template rows >= min-row whose cells carry a status fill (orange = error, yellow = warning, green = success)
     with SKU, EAN/ID and the flagged cells;
  3. an Error Fingerprint per (marketplace, sku, code, attribute, original value) when the summary names an impacted
     column; otherwise a row-level finding with code UNMAPPED.
Colour is evidence, never the only truth: every colour finding is labelled source=FILL and must be matched to the
summary / error message before it is treated as an error. Rows are NOT edited; this script never writes.
"""
import argparse
import colorsys
import hashlib
import json
import re
import sys

from xlsx_core import M, TEMPLATE_NAME_HINTS, Book, col_to_idx, idx_to_col, parse_xml, split_ref

SYN = {
    "code": ["error code", "fehlercode", "code d'erreur", "codice errore", "código de error", "codigo de error",
             "kod błędu", "foutcode", "felkod", "код ошибки", "エラーコード"],
    "category": ["category of error", "fehlerkategorie", "catégorie", "categoria", "categoría", "kategoria",
                 "категория"],
    "message": ["error message", "fehlermeldung", "message d'erreur", "messaggio di errore", "mensaje de error",
                "komunikat", "foutmelding", "felmeddelande", "сообщение"],
    "field": ["affected field", "betroffenes feld", "champ concerné", "campo interessato", "campo afectado",
              "dotyczy pola", "betrokken veld", "berörd fält", "поле"],
    "column": ["impacted column", "betroffene spalte", "colonne concernée", "colonna interessata", "columna afectada",
               "kolumna", "betrokken kolom", "berörd kolumn", "столбец"],
    "count": ["number of errors", "anzahl", "nombre d'erreurs", "numero di errori", "número de errores",
              "liczba błędów", "aantal fouten", "antal fel", "количество"],
}


def classify_fill(rgb):
    if not rgb or len(rgb) < 6:
        return None
    r, g, b = int(rgb[-6:-4], 16), int(rgb[-4:-2], 16), int(rgb[-2:], 16)
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    if s < 0.18 or v < 0.35:
        return None
    deg = h * 360
    if deg < 15 or deg >= 345:
        return "red"
    if deg < 42:
        return "orange"
    if deg < 70:
        return "yellow"
    if 80 <= deg <= 170:
        return "green"
    return "other"


def style_fills(book):
    data = book.entries.get("xl/styles.xml")
    if not data:
        return {}
    root = parse_xml(data)
    fills = []
    fe = root.find(M + "fills")
    for f in (fe if fe is not None else []):
        pf = f.find(M + "patternFill")
        rgb = None
        if pf is not None and pf.get("patternType") not in (None, "none"):
            fg = pf.find(M + "fgColor")
            if fg is not None:
                rgb = fg.get("rgb")
        fills.append(rgb)
    xfs = []
    cx = root.find(M + "cellXfs")
    for xf in (cx if cx is not None else []):
        xfs.append(fills[int(xf.get("fillId", 0))] if int(xf.get("fillId", 0)) < len(fills) else None)
    return {i: classify_fill(rgb) for i, rgb in enumerate(xfs)}


def find_summary(book):
    for s in book.sheets:
        rows = list(book.rows(s["name"], 1, 400))
        for r, cells in rows:
            labels = {c: str(v[1]).strip().lower() for c, v in cells.items() if v[0] == "text"}
            hit = {}
            for col, lab in labels.items():
                for key, syns in SYN.items():
                    if any(lab == x or lab.startswith(x) for x in syns):
                        hit.setdefault(key, col)
            if "code" in hit and ("message" in hit or "field" in hit):
                out = []
                for r2, cells2 in rows:
                    if r2 <= r:
                        continue
                    if not cells2:
                        if out:
                            break
                        continue
                    rec = {k: (cells2.get(c, (None, None))[1]) for k, c in hit.items()}
                    if rec.get("code") is None and rec.get("message") is None:
                        if out:
                            break
                        continue
                    out.append(dict(rec, summary_row=r2))
                return s["name"], r, out
    return None, None, []


def fp(*parts):
    return hashlib.sha1("|".join("" if p is None else str(p) for p in parts).encode("utf-8")).hexdigest()[:16]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--marketplace", required=True)
    ap.add_argument("--sheet")
    ap.add_argument("--header-row", type=int, default=5)
    ap.add_argument("--min-row", type=int, default=7)
    ap.add_argument("--sku-key", default="item_sku")
    ap.add_argument("--json")
    a = ap.parse_args()

    book = Book(a.file)
    sheet = a.sheet or next((s["name"] for s in book.sheets if TEMPLATE_NAME_HINTS.match(s["name"])), None)
    if not sheet:
        sys.exit("cannot identify the data sheet; pass --sheet (and confirm it with the user)")
    sum_sheet, sum_hdr, summary = find_summary(book)
    headers = {c: str(v[1]) for c, v in dict(book.rows(sheet, a.header_row, a.header_row)).get(a.header_row, {}).items()}
    by_key = {v: c for c, v in headers.items()}
    fills = style_fills(book)

    # template rows with status colours
    root = book.sheet_root(sheet)
    rows_out = []
    id_cols = [c for c, k in headers.items() if re.search(r"(external_product_id|product_id|ean|upc|gtin)$", k, re.I)]
    sku_col = by_key.get(a.sku_key) or next((c for c, k in headers.items() if re.search(r"sku", k, re.I)), None)
    sd = root.find(M + "sheetData")
    for row in sd:
        rn = int(row.get("r"))
        if rn < a.min_row:
            continue
        flagged, texts = [], {}
        for c in row:
            col, _ = split_ref(c.get("r"))
            kind, val = book.cell_value(c)
            texts[col] = val
            color = fills.get(int(c.get("s", 0)))
            if color in ("red", "orange", "yellow"):
                flagged.append(dict(cell=c.get("r"), field=headers.get(col), color=color, value=val if kind != "empty" else None,
                                    severity={"red": "ERROR", "orange": "ERROR", "yellow": "WARNING"}[color]))
        if flagged:
            rows_out.append(dict(row=rn, sku=texts.get(sku_col), ids=[texts.get(c) for c in id_cols if texts.get(c)],
                                 flagged_cells=flagged))

    # map summary lines to rows via impacted column
    findings = []
    for s in summary:
        colspec = str(s.get("column") or "").strip()
        letters = re.findall(r"\b([A-Z]{1,3})\b", colspec.upper()) if re.fullmatch(r"[A-Za-z, ]+", colspec) else []
        target_cols = [c for c in letters if c in headers] or ([by_key[s["field"]]] if s.get("field") in by_key else [])
        matched = False
        for r in rows_out:
            for fc in r["flagged_cells"]:
                col = split_ref(fc["cell"])[0]
                if col in target_cols:
                    matched = True
                    findings.append(dict(marketplace=a.marketplace, sku=r["sku"], ids=r["ids"], row=r["row"], cell=fc["cell"],
                                         attribute=fc["field"], original_value=fc["value"], error_code=s.get("code"),
                                         error_message=s.get("message"), category=s.get("category"),
                                         severity=fc["severity"], source="SUMMARY+FILL",
                                         fingerprint=fp(a.marketplace, r["sku"], s.get("code"), fc["field"], fc["value"])))
        if not matched:
            findings.append(dict(marketplace=a.marketplace, sku=None, row=None, cell=None, attribute=s.get("field"),
                                 error_code=s.get("code"), error_message=s.get("message"), category=s.get("category"),
                                 severity="UNKNOWN", source="SUMMARY_ONLY", count=s.get("count"),
                                 impacted_column=s.get("column"),
                                 fingerprint=fp(a.marketplace, None, s.get("code"), s.get("field"), s.get("column")),
                                 note="no flagged Template cell matched this summary line: map manually"))
    colour_only = [r for r in rows_out if not any(f["row"] == r["row"] for f in findings if f.get("row"))]
    for r in colour_only:
        for fc in r["flagged_cells"]:
            findings.append(dict(marketplace=a.marketplace, sku=r["sku"], ids=r["ids"], row=r["row"], cell=fc["cell"],
                                 attribute=fc["field"], original_value=fc["value"], error_code="UNMAPPED",
                                 error_message=None, severity=fc["severity"], source="FILL_ONLY",
                                 fingerprint=fp(a.marketplace, r["sku"], "UNMAPPED", fc["field"], fc["value"]),
                                 note="coloured cell without a summary line: colour is never the only truth - verify"))
    res = dict(file=a.file, marketplace=a.marketplace, template_sheet=sheet, summary_sheet=sum_sheet,
               summary_lines=len(summary), flagged_rows=len(rows_out), findings=findings,
               totals=dict(errors=sum(f["severity"] == "ERROR" for f in findings),
                           warnings=sum(f["severity"] == "WARNING" for f in findings),
                           unknown=sum(f["severity"] == "UNKNOWN" for f in findings)))
    text = json.dumps(res, ensure_ascii=False, indent=2, default=str)
    if a.json:
        open(a.json, "w", encoding="utf-8").write(text + "\n")
    print(f"summary sheet: {sum_sheet} ({len(summary)} lines); template '{sheet}': {len(rows_out)} flagged rows; "
          f"findings: {res['totals']}")
    for f in findings[:40]:
        print(f"  {f['severity']:8} {str(f['error_code']):8} row={f.get('row')} cell={f.get('cell')} attr={f.get('attribute')} "
              f"sku={f.get('sku')} [{f['source']}]")
    if not a.json:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
