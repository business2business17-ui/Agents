"""Минимальное чтение .xlsx и .csv без внешних зависимостей (только первый лист).

Поддерживает то, что встречается в экспортах Helium 10: shared strings, inline strings,
числовые ячейки, пропущенные ячейки (по адресу r="C5").
"""
from __future__ import annotations

import csv
import re
import zipfile
import xml.etree.ElementTree as ET

_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
_REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
_COL = re.compile(r"([A-Z]+)")


def _col_index(ref: str) -> int:
    letters = _COL.match(ref).group(1)
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def _text(el) -> str:
    return "".join(t.text or "" for t in el.iter(f"{{{_NS['m']}}}t"))


def _first_sheet_path(z: zipfile.ZipFile) -> str:
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    sheet = wb.find("m:sheets/m:sheet", _NS)
    rid = sheet.get(_REL_NS) if sheet is not None else None
    if rid and "xl/_rels/workbook.xml.rels" in z.namelist():
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        for rel in rels:
            if rel.get("Id") == rid:
                target = rel.get("Target").lstrip("/")
                return target if target.startswith("xl/") else "xl/" + target
    return "xl/worksheets/sheet1.xml"


def read_xlsx(path: str) -> list:
    """→ список строк (list[str|None]); первая строка — заголовок."""
    with zipfile.ZipFile(path) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            shared = [_text(si) for si in root.findall("m:si", _NS)]
        root = ET.fromstring(z.read(_first_sheet_path(z)))
    rows = []
    for row in root.iter(f"{{{_NS['m']}}}row"):
        cells = {}
        for c in row.findall("m:c", _NS):
            t, ref = c.get("t"), c.get("r")
            if t == "inlineStr":
                val = _text(c)
            else:
                v = c.find("m:v", _NS)
                val = None if v is None else v.text
                if t == "s" and val is not None:
                    val = shared[int(val)]
            idx = _col_index(ref) if ref else len(cells)
            cells[idx] = val
        rows.append([cells.get(i) for i in range(max(cells) + 1)] if cells else [])
    return rows


def read_table(path: str) -> list:
    """xlsx или csv → список словарей по заголовку первой строки."""
    if path.lower().endswith(".csv"):
        with open(path, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.reader(f))
    else:
        rows = read_xlsx(path)
    if not rows:
        return []
    header = [(h or "").strip() for h in rows[0]]
    out = []
    for r in rows[1:]:
        if not any(v not in (None, "") for v in r):
            continue
        r = list(r) + [None] * (len(header) - len(r))
        out.append(dict(zip(header, r)))
    return out
