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
Two report layouts are supported:
  LEGACY  summary table per error code + status colours on Template cells (above);
  STATUS  (current Seller Central download "Feed Processing Summary"): the Template gets leading status columns
          (::submission_status, ::number_of_attributes_with_errors, ::number_of_attributes_with_other_suggestions) and the
          summary sheet carries two tables - per error code and per SKU (code, message, SKU, "impacted cell" = the STATUS cell of
          that row, e.g. B35, NOT the faulty attribute). The offending attribute is derived from the message (media URL found in
          the row, "Your generic_keyword contains ..."); when it cannot be derived the finding is row-level (attribute null).
          Because of the 3 leading columns, cell letters of this workbook differ from the originally uploaded feed: patches
          must address attributes by key (header row 5) + SKU, never by the letters in this report.
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
    "sku": ["sku"],
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


URL_RX = re.compile(r"https?://[^\s\"'<>]+")
ATTR_RX = re.compile(r"\bYour ([a-z][a-z0-9_]+) contains\b", re.I)
TERMS_RX = re.compile(r"\[([^\]]+)\]")
CELL_RX = re.compile(r"\(([A-Z]{1,3})(\d+)?\)\s*$")
DEPENDS = {"13013": ["100730", "18299", "5461", "8541", "8542"]}  # consequence codes: fix the cause, not the offer


def all_sections(book):
    """Every error table of the summary sheet -> (sheet, [ {kind, header_row, lines} ], reported_totals)."""
    for s in book.sheets:
        rows = list(book.rows(s["name"], 1, 60000))
        out, totals = [], {}
        i = 0
        while i < len(rows):
            r, cells = rows[i]
            labels = {c: str(v[1]).strip().lower() for c, v in cells.items() if v[0] == "text"}
            first = next(iter(labels.values()), "")
            if first.startswith("number of skus") or first.startswith("total number of"):
                nums = [v[1] for v in cells.values() if v[0] != "text" or re.fullmatch(r"-?\d+", str(v[1]))]
                if nums:
                    totals[first] = nums[-1]
            hit = {}
            for col, lab in labels.items():
                for key, syns in SYN.items():
                    if any(lab == x or lab.startswith(x) for x in syns):
                        hit.setdefault(key, col)
            if "code" in hit and ("message" in hit or "field" in hit):
                lines, j = [], i + 1
                while j < len(rows):
                    r2, c2 = rows[j]
                    rec = {k: (c2.get(c, (None, None))[1]) for k, c in hit.items()}
                    f0 = str(next(iter(c2.values()))[1]).strip().lower() if c2 else ""
                    if not c2 or rec.get("code") is None and rec.get("message") is None or f0.startswith(("total", "errors and warnings")):
                        break
                    lines.append(dict(rec, summary_row=r2))
                    j += 1
                out.append(dict(kind="per_sku" if "sku" in hit else "per_code", header_row=r, lines=lines))
                i = j
                continue
            i += 1
        if out:
            return s["name"], out, totals
    return None, [], {}


def status_columns(headers):
    return {k: c for c, k in headers.items() if str(k).startswith("::")}


def infer_attribute(message, row_vals, headers):
    """Find the faulty attribute of one SKU from the error message. row_vals: {col: value}. Returns dict or None."""
    msg = str(message or "")
    by_col = {c: str(headers.get(c, "")) for c in row_vals}
    for url in URL_RX.findall(msg):
        url = url.rstrip(".,;)")
        for c, v in row_vals.items():
            if v is not None and str(v).strip() == url:
                return dict(attribute=by_col[c], column=c, original_value=v, how="MEDIA_URL_FOUND_IN_ROW", confidence="HIGH")
    m = ATTR_RX.search(msg)
    if m:
        key = m.group(1).lower()
        for c, k in headers.items():
            if k.lower() == key or k.lower().startswith(key + "[") or k.lower().startswith(key + "#"):
                v = row_vals.get(c)
                out = dict(attribute=k, column=c, original_value=v, how="NAMED_IN_MESSAGE", confidence="HIGH")
                terms = TERMS_RX.findall(msg)
                if terms and v:
                    bad = [t.strip() for t in re.split(r"[,;]", ",".join(terms)) if t.strip()]
                    new = str(v)
                    for t in bad:
                        new = re.sub(r"(?<!\w)" + re.escape(t) + r"(?!\w)", "", new, flags=re.I)
                    new = re.sub(r"\s{2,}", " ", new).strip()
                    out.update(terms=bad, proposed_value=new, proposed_how="remove the flagged term(s) only; user approval required")
                return out
    return None


def fp(*parts):
    return hashlib.sha1("|".join("" if p is None else str(p) for p in parts).encode("utf-8")).hexdigest()[:16]


def parse_status_layout(a, book, sheet, sum_sheet, per_code, per_sku, reported, headers):
    sku_col = next((c for c, k in headers.items() if k == "contribution_sku#1.value"), None) or \
        next((c for c, k in headers.items() if re.search(r"sku", k, re.I) and not k.startswith("::")), None)
    st = status_columns(headers)
    rows = {}
    for r, cells in book.rows(sheet, a.min_row):
        rows[r] = {c: v[1] for c, v in cells.items()}
    status_col = st.get("::submission_status")
    sku_row = {}
    for r, vals in rows.items():
        if sku_col and vals.get(sku_col) is not None:
            sku_row.setdefault(str(vals[sku_col]).strip(), r)
    status_counts = {}
    for r, vals in rows.items():
        if status_col and vals.get(status_col) is not None:
            k = str(vals[status_col])
            status_counts[k] = status_counts.get(k, 0) + 1
    findings, unmatched = [], 0
    for ln in per_sku["lines"]:
        sku = str(ln.get("sku") or "").strip()
        m = CELL_RX.search(str(ln.get("field") or ""))
        row = int(m.group(2)) if m and m.group(2) else sku_row.get(sku)
        if row is not None and sku and sku_row.get(sku) not in (None, row):
            row = sku_row[sku]  # the SKU decides, the cell in the report is only a status cell
        vals = rows.get(row, {})
        if sku and not vals:
            unmatched += 1
        inf = infer_attribute(ln.get("message"), vals, headers) or {}
        code = str(ln.get("code"))
        f = dict(marketplace=a.marketplace, sku=sku or None, row=row, report_cell=(f"{m.group(1)}{m.group(2)}" if m and m.group(2) else None),
                 cell=(f"{inf['column']}{row}" if inf.get("column") and row else None), attribute=inf.get("attribute"),
                 original_value=inf.get("original_value"), error_code=code, error_message=ln.get("message"), category=ln.get("category"),
                 severity="ERROR" if str(ln.get("category", "")).upper().startswith("ERR") else
                 ("WARNING" if str(ln.get("category", "")).upper().startswith("WARN") else "UNKNOWN"),
                 source="SUMMARY_SKU+TEMPLATE", attribute_source=inf.get("how") or "NOT_DERIVABLE (row-level)",
                 confidence=inf.get("confidence"), depends_on_codes=DEPENDS.get(code, []),
                 fingerprint=fp(a.marketplace, sku, code, inf.get("attribute"), inf.get("original_value") or ln.get("message")))
        for k in ("terms", "proposed_value", "proposed_how"):
            if k in inf:
                f[k] = inf[k]
        findings.append(f)
    # groups: same code + message shape (URLs/terms stripped)
    groups = {}
    for f in findings:
        shape = URL_RX.sub("<URL>", str(f["error_message"] or ""))
        g = groups.setdefault((f["error_code"], shape), dict(error_code=f["error_code"], category=f["category"], message_shape=shape[:300],
                                                            errors=0, skus=set(), attributes=set(), depends_on_codes=f["depends_on_codes"]))
        g["errors"] += 1
        if f["sku"]:
            g["skus"].add(f["sku"])
        if f["attribute"]:
            g["attributes"].add(f["attribute"].split("[")[0])
    grp = [dict(g, skus=len(g["skus"]), sku_examples=sorted(g["skus"])[:5], attributes=sorted(g["attributes"])) for g in groups.values()]
    grp.sort(key=lambda g: -g["errors"])
    # settings line of the template (first row, first cell): feed timestamp / type / marketplace
    first = next(iter(book.rows(sheet, 1, 1)), (1, {}))[1]
    settings = str(first.get("A", (None, ""))[1]) if first else ""
    ts = re.search(r"timestamp=([^&]+)", settings)
    res = dict(file=a.file, marketplace=a.marketplace, layout="STATUS", template_sheet=sheet, summary_sheet=sum_sheet,
               feed_timestamp=ts.group(1) if ts else None, status_columns=list(st.keys()), reported_totals=reported,
               submission_status_counts=status_counts, rows_in_template=len(rows),
               per_code_lines=len(per_code["lines"]) if per_code else 0, per_sku_lines=len(per_sku["lines"]), groups=grp, findings=findings,
               warnings_on_use=["Cell letters in this report include 3 leading status columns that the uploaded feed does not have: "
                                "address attributes by key + SKU when patching the original feed.",
                                "Errors that depend on another error (depends_on_codes) are consequences: fix the cause first."],
               totals=dict(errors=sum(f["severity"] == "ERROR" for f in findings), warnings=sum(f["severity"] == "WARNING" for f in findings),
                           unknown=sum(f["severity"] == "UNKNOWN" for f in findings),
                           row_level_without_attribute=sum(1 for f in findings if not f["attribute"]), sku_not_found_in_template=unmatched))
    if per_code and sum(int(x.get("count") or 0) for x in per_code["lines"]) != len(findings):
        res["warnings_on_use"].append(f"per-code table counts {sum(int(x.get('count') or 0) for x in per_code['lines'])} errors, "
                                      f"per-SKU table lists {len(findings)}: check for truncation")
    if a.json:
        open(a.json, "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=2, default=str) + "\n")
    print(f"STATUS layout | summary '{sum_sheet}' | template '{sheet}' {len(rows)} rows | reported: "
          + "; ".join(f"{k}={v}" for k, v in reported.items()))
    print(f"submission status counts: {status_counts}")
    print(f"findings: {res['totals']}")
    for g in grp:
        print(f"  {g['errors']:5} errors / {g['skus']:5} SKUs  code {g['error_code']:7} {g['category']}  attrs={g['attributes'] or '-'}"
              f"{'  depends_on=' + ','.join(g['depends_on_codes']) if g['depends_on_codes'] else ''}  {g['message_shape'][:90]}")
    return 0


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

    sec_sheet, sections, reported = all_sections(book)
    per_sku = next((x for x in sections if x["kind"] == "per_sku"), None)
    per_code = next((x for x in sections if x["kind"] == "per_code"), None)
    if per_sku and per_sku["lines"]:
        return parse_status_layout(a, book, sheet, sec_sheet, per_code, per_sku, reported, headers)

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
