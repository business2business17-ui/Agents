#!/usr/bin/env python3
"""Recognize Amazon Seller Central reports by their column signature (references/report-detection.md sections 1-3).

  report_detect.py FILE [FILE ...] [--json]
Per file: report type + match % (>= 70 recognized, 40-70 probable with the missing columns, < 40 unknown: show the header and ask),
header row (the first row with >= 3 signature columns; Date Range Reports have 7-8 disclaimer rows above it), encoding, delimiter,
decimal format (1.234,56 vs 1,234.56), row count (0 = "no data for the period", not an error), marketplace / period / currency
(content first, then the file name, marked "by file name"), sha256 (identical hash = duplicate file).
Column names are normalized (case, BOM, spaces / hyphens / underscores) and DE / FR / IT / ES Date Range headers are mapped to English.
Exit 0 = all files recognized or probable, 1 = at least one unknown file, 2 = unreadable input.
"""
import argparse
import csv
import hashlib
import io
import json
import re
import sys

LOCAL = {  # localized Date Range Report headers -> English
    "datum/uhrzeit": "date/time", "date/heure": "date/time", "data/ora": "date/time", "fecha y hora": "date/time",
    "abrechnungsnummer": "settlement id", "numero de versement": "settlement id", "numéro de versement": "settlement id",
    "numero pagamento": "settlement id", "identificador de pago": "settlement id",
    "typ": "type", "tipo": "type",
    "bestellnummer": "order id", "numéro de la commande": "order id", "numero ordine": "order id", "número de pedido": "order id",
    "menge": "quantity", "quantité": "quantity", "quantità": "quantity", "cantidad": "quantity",
    "umsätze": "product sales", "ventes de produits": "product sales", "vendite": "product sales", "ventas de productos": "product sales",
    "verkaufsgebühren": "selling fees", "frais de vente": "selling fees", "commissioni di vendita": "selling fees", "tarifas de venta": "selling fees",
    "gebühren zu versand durch amazon": "fba fees", "frais expédié par amazon": "fba fees",
    "costi del servizio logistica di amazon": "fba fees", "tarifas de logística de amazon": "fba fees",
    "andere transaktionsgebühren": "other transaction fees", "autres frais de transaction": "other transaction fees",
    "altri costi relativi alle transazioni": "other transaction fees", "tarifas de otras transacciones": "other transaction fees",
    "andere": "other", "autre": "other", "altro": "other", "otro": "other",
    "gesamt": "total", "totale": "total",
}
R = re.compile
SIGNATURES = [  # (type, application, key columns; a str starting with "re:" is a regex on the normalized header)
    ("Date Range / Transaction Report", "P&L source", ["date/time", "settlement id", "type", "order id", "sku", "quantity", "marketplace",
                                                       "product sales", "selling fees", "fba fees", "other transaction fees", "other", "total"]),
    ("Settlement Report (Flat File V2)", "payout, bank reconciliation", ["settlement id", "settlement start date", "settlement end date", "deposit date",
                                                                          "total amount", "currency", "transaction type", "order id", "amount type",
                                                                          "amount description", "amount", "posted date", "sku"]),
    ("All Orders Report", "orders, cancellations, pending", ["amazon order id", "purchase date", "order status", "fulfillment channel", "sales channel",
                                                             "sku", "asin", "quantity", "currency", "item price", "item tax", "promotion discount"]),
    ("Business Report (Detail Page Sales and Traffic by Child Item)", "traffic, conversion", ["(parent) asin", "(child) asin", "title", "sessions", "page views",
                                                                                              "unit session percentage", "units ordered", "ordered product sales", "total order items"]),
    ("Business Report (Sales and Orders by ASIN)", "orders / refunds by ASIN; no traffic", ["(child) asin", "units ordered", "ordered product sales", "total order items",
                                                                                           "units refunded", "refund rate", "shipped product sales", "units shipped", "orders shipped"]),
    ("Payments Transactions view", "orders and service payments, aggregated fees", ["date", "transaction status", "transaction type", "order id", "product details",
                                                                                     "total product charges", "total promotional rebates", "amazon fees", "other", "re:^total \\(\\w{3}\\)$"]),
    ("FBA Manage Inventory", "stock", ["sku", "fnsku", "asin", "product name", "afn fulfillable quantity", "afn reserved quantity", "afn inbound working quantity",
                                       "afn inbound shipped quantity", "afn inbound receiving quantity", "afn unsellable quantity"]),
    ("Inventory Ledger (Detailed)", "stock movement, lost / damaged", ["date", "fnsku", "asin", "msku", "event type", "reference id", "quantity", "fulfillment center", "disposition", "reason"]),
    ("Inventory Ledger (Summary)", "stock reconciliation", ["date", "fnsku", "msku", "starting warehouse balance", "receipts", "customer shipments", "customer returns", "vendor returns",
                                                           "found", "lost", "damaged", "disposed", "other events", "ending warehouse balance"]),
    ("FBA Customer Returns", "returns, sellable / unsellable", ["return date", "order id", "sku", "asin", "fnsku", "quantity", "fulfillment center id", "detailed disposition", "reason", "status"]),
    ("Reimbursements", "Amazon compensation", ["approval date", "reimbursement id", "case id", "amazon order id", "reason", "sku", "fnsku", "asin", "condition", "currency unit",
                                               "amount per unit", "amount total", "quantity reimbursed cash", "quantity reimbursed inventory"]),
    ("Monthly Storage Fees", "storage", ["asin", "fnsku", "fulfillment center", "country code", "item volume", "average quantity on hand", "month of charge", "storage rate", "currency", "estimated monthly storage fee"]),
    ("Aged Inventory Surcharge / LTSF", "aged inventory", ["snapshot date", "sku", "fnsku", "asin", "qty charged", "amount charged", "surcharge age tier", "currency"]),
    ("FBA Fee Preview", "expected fees for leakage checks", ["sku", "asin", "product group", "price", "longest side", "median side", "shortest side", "item package weight",
                                                            "product size tier", "estimated referral fee per unit", "expected fulfillment fee per unit"]),
    ("Sponsored Products Advertised Product", "ads by SKU", ["re:^(date|start date)$", "campaign name", "ad group name", "advertised sku", "advertised asin", "impressions", "clicks",
                                                             "spend", "re:^7 day total sales", "re:^7 day total orders", "re:^7 day total units"]),
    ("Sponsored Products Search Term", "wasted search terms", ["customer search term", "targeting", "match type", "impressions", "clicks", "spend", "re:^7 day total sales"]),
    ("Sponsored Brands / Display Campaign", "SB / SD ads", ["campaign name", "impressions", "clicks", "spend", "re:^14 day total sales", "re:^14 day total orders"]),
    ("Cost Master (user)", "COGS", ["sku", "currency", "purchase cost"]),
    ("Bank Statement", "actual cash flow", ["re:^(date|booking date|buchungstag|data)$", "re:^(amount|betrag|importo|debit|credit)$", "re:^(description|details|purpose|verwendungszweck|counterparty|beneficiary)$"]),
]
MARKETS = [("UK", R(r"(?<![a-z])(uk|gb|united kingdom)(?![a-z])", re.I), "GBP"), ("DE", R(r"(?<![a-z])(de|germany|deutschland)(?![a-z])", re.I), "EUR"),
           ("FR", R(r"(?<![a-z])(fr|france)(?![a-z])", re.I), "EUR"), ("IT", R(r"(?<![a-z])(it|italy|italia)(?![a-z])", re.I), "EUR"),
           ("ES", R(r"(?<![a-z])(es|spain|espa(n|ñ)a)(?![a-z])", re.I), "EUR"), ("NL", R(r"(?<![a-z])(nl|netherlands)(?![a-z])", re.I), "EUR"),
           ("PL", R(r"(?<![a-z])(pl|poland)(?![a-z])", re.I), "PLN"), ("SE", R(r"(?<![a-z])(se|sweden)(?![a-z])", re.I), "SEK"),
           ("BE", R(r"(?<![a-z])(be|belgium|belgique)(?![a-z])", re.I), "EUR"), ("IE", R(r"(?<![a-z])(ie|ireland)(?![a-z])", re.I), "EUR"),
           ("US", R(r"(?<![a-z])(us|usa)(?![a-z])", re.I), "USD")]
DOMAINS = {"amazon.de": ("DE", "EUR"), "amazon.fr": ("FR", "EUR"), "amazon.it": ("IT", "EUR"), "amazon.es": ("ES", "EUR"), "amazon.nl": ("NL", "EUR"),
           "amazon.pl": ("PL", "PLN"), "amazon.se": ("SE", "SEK"), "amazon.com.be": ("BE", "EUR"), "amazon.ie": ("IE", "EUR"),
           "amazon.co.uk": ("UK", "GBP"), "amazon.com": ("US", "USD")}


def norm(h):
    h = str(h or "").replace("﻿", "").strip().lower()
    h = LOCAL.get(h, h)
    h = re.sub(r"[\s_\-]+", " ", h).strip()
    return LOCAL.get(h, h)


def key_hit(key, headers):
    if key.startswith("re:"):
        rx = re.compile(key[3:])
        return any(rx.search(h) for h in headers)
    return key in headers


def score(headers):
    best = None
    for name, use, keys in SIGNATURES:
        hit = [k for k in keys if key_hit(k, headers)]
        pct = len(hit) / len(keys) * 100
        if best is None or pct > best[0]:
            best = (pct, name, use, [k for k in keys if k not in hit])
    return best


def decode(raw):
    for enc in ("utf-8-sig", "cp1252", "cp1251"):
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1"), "latin-1"


def read_rows(path, raw):
    if path.lower().endswith((".xlsx", ".xlsm")):
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
        ws = wb.worksheets[0]
        return [list(r) for r in ws.iter_rows(values_only=True)], "xlsx", None
    text, enc = decode(raw)
    sample = "\n".join(text.splitlines()[:30])
    try:
        delim = csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except csv.Error:
        delim = "\t" if "\t" in sample else ","
    return list(csv.reader(io.StringIO(text), delimiter=delim)), enc, delim


def decimal_format(rows):
    eu = us = 0
    for r in rows[:300]:
        for c in r:
            s = str(c)
            if re.fullmatch(r"-?\(?\d{1,3}(\.\d{3})*,\d{1,2}\)?", s.strip()):
                eu += 1
            elif re.fullmatch(r"-?\(?\d{1,3}(,\d{3})*\.\d{1,2}\)?", s.strip()):
                us += 1
    return "european (1.234,56)" if eu > us else "english (1,234.56)" if us else "unknown"


def from_name(name):
    out = {}
    low = name.lower()
    for dom, (mk, cur) in DOMAINS.items():
        if dom in low:
            out.update(marketplace=mk, currency=cur)
            break
    if "marketplace" not in out:
        for mk, rx, cur in MARKETS:
            if rx.search(name):
                out.update(marketplace=mk, currency=cur)
                break
    m = re.search(r"(\d{4}-\d{2}-\d{2})\D+(\d{4}-\d{2}-\d{2})", name) or re.search(r"(\d{2}\.\d{2}\.\d{4})\D+(\d{2}\.\d{2}\.\d{4})", name)
    if m:
        out["period"] = f"{m.group(1)} .. {m.group(2)}"
    elif re.search(r"last[\s_-]*(\d+)[\s_-]*days", low):
        out["period"] = "last " + re.search(r"last[\s_-]*(\d+)", low).group(1) + " days (relative to the file date)"
    if out:
        out["source"] = "by file name"
    return out


def analyse(path):
    import os
    raw = open(path, "rb").read()
    rows, enc, delim = read_rows(path, raw)
    info = dict(file=os.path.basename(path), sha256=hashlib.sha256(raw).hexdigest(), encoding=enc, delimiter=delim)
    header_i, best = None, None
    for i, r in enumerate(rows[:40]):
        hs = [norm(c) for c in r if str(c or "").strip()]
        if len(hs) < 3:
            continue
        sc = score(hs)
        if sc and (best is None or sc[0] > best[0]):
            best, header_i = sc, i
    if best is None:
        info.update(type="unknown", match_pct=0, status="unknown", note="no header row with >= 3 columns found", first_rows=[list(map(str, r))[:8] for r in rows[:3]])
        return info
    headers = [norm(c) for c in rows[header_i]]
    pct, name, use, missing = best
    status = "recognized" if pct >= 70 else "probable" if pct >= 40 else "unknown"
    data = [r for r in rows[header_i + 1:] if any(str(c or "").strip() for c in r)]
    info.update(type=name if status != "unknown" else "unknown", closest=name, application=use, match_pct=round(pct), status=status,
                missing_columns=missing if status != "recognized" else [], header_row=header_i + 1, rows=len(data),
                decimal_format=decimal_format(data))
    if status == "unknown":
        info["header"] = [str(c) for c in rows[header_i]][:12]
        info["note"] = "show this header to the user and ask what the report is"
    if not data:
        info["note"] = "header only: no data for the period (not an error)"
    cur = next((re.search(r"\((\w{3})\)", str(c)).group(1) for c in rows[header_i] if re.search(r"\((EUR|GBP|USD|PLN|SEK)\)", str(c))), None)
    meta = from_name(info["file"])
    if cur:
        info["currency"] = cur
        info["currency_source"] = "header"
    elif meta.get("currency"):
        info["currency"], info["currency_source"] = meta["currency"], "by file name / marketplace"
    for k in ("marketplace", "period"):
        if meta.get(k):
            info[k], info[k + "_source"] = meta[k], "by file name"
    return info


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    res, seen, rc = [], {}, 0
    for f in a.files:
        try:
            info = analyse(f)
        except (OSError, ValueError) as e:
            print(f"{f}: {e}", file=sys.stderr)
            return 2
        if info["sha256"] in seen:
            info["duplicate_of"] = seen[info["sha256"]]
        seen.setdefault(info["sha256"], info["file"])
        if info["status"] == "unknown":
            rc = 1
        res.append(info)
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        for i in res:
            print(f"{i['file']}: {i['type']} ({i['match_pct']}% {i['status']}) rows={i.get('rows')} currency={i.get('currency')} "
                  f"marketplace={i.get('marketplace')} period={i.get('period')}" + (f" DUPLICATE of {i['duplicate_of']}" if i.get("duplicate_of") else "")
                  + (f" NOTE: {i['note']}" if i.get("note") else ""))
    return rc


if __name__ == "__main__":
    sys.exit(main())
