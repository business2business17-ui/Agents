"""Low-level, dependency-light helpers for reading Amazon .xlsx/.xlsm files at the ZIP/XML level.

Working at XML level (instead of load/save through a spreadsheet library) lets the other scripts change
ONE sheet part and keep every other byte of the workbook (macros, validations, styles, hidden state)
identical. Requires lxml.
"""
import hashlib
import posixpath
import re
import zipfile

from lxml import etree

NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
M = "{%s}" % NS_MAIN
R = "{%s}" % NS_REL


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_zip(path):
    """Return (ordered list of (ZipInfo, bytes))."""
    with zipfile.ZipFile(path) as zf:
        return [(zi, zf.read(zi.filename)) for zi in zf.infolist()]


def col_to_idx(col: str) -> int:
    n = 0
    for ch in col.upper():
        n = n * 26 + (ord(ch) - 64)
    return n


def idx_to_col(i: int) -> str:
    s = ""
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


_CELL_RE = re.compile(r"^([A-Za-z]{1,3})(\d+)$")


def split_ref(ref: str):
    m = _CELL_RE.match(ref)
    if not m:
        raise ValueError(f"bad cell reference: {ref!r}")
    return m.group(1).upper(), int(m.group(2))


def parse_xml(data: bytes):
    return etree.fromstring(data, etree.XMLParser(remove_blank_text=False, resolve_entities=False, huge_tree=True))


def serialize(root) -> bytes:
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


class Book:
    """Read-only view of a workbook package."""

    def __init__(self, path):
        self.path = path
        self.entries = {zi.filename: data for zi, data in read_zip(path)}
        wb = parse_xml(self.entries["xl/workbook.xml"])
        rels = parse_xml(self.entries["xl/_rels/workbook.xml.rels"])
        rid_to_target = {}
        for rel in rels:
            tgt = rel.get("Target")
            tgt = tgt.lstrip("/") if tgt.startswith("/") else posixpath.normpath(posixpath.join("xl", tgt))
            rid_to_target[rel.get("Id")] = tgt
        self.sheets = []
        for s in wb.find(M + "sheets"):
            self.sheets.append(dict(name=s.get("name"), sheet_id=s.get("sheetId"),
                                    state=s.get("state", "visible"), part=rid_to_target.get(s.get(R + "id"))))
        self.defined_names = []
        dn = wb.find(M + "definedNames")
        if dn is not None:
            for n in dn:
                self.defined_names.append(dict(name=n.get("name"), local=n.get("localSheetId"),
                                               hidden=n.get("hidden"), ref=(n.text or "")))
        self.workbook_root = wb
        self._shared = None

    @property
    def has_macros(self):
        return "xl/vbaProject.bin" in self.entries

    def shared_strings(self):
        if self._shared is None:
            self._shared = []
            data = self.entries.get("xl/sharedStrings.xml")
            if data:
                root = parse_xml(data)
                for si in root.findall(M + "si"):
                    self._shared.append("".join(t.text or "" for t in si.iter(M + "t")))
        return self._shared

    def sheet_part(self, name):
        for s in self.sheets:
            if s["name"] == name:
                return s["part"]
        raise KeyError(f"sheet not found: {name!r}; sheets: {[s['name'] for s in self.sheets]}")

    def sheet_root(self, name):
        return parse_xml(self.entries[self.sheet_part(name)])

    def cell_value(self, c):
        """(kind, value) of a <c> element. kind in text|number|bool|error|formula|empty."""
        t = c.get("t")
        f = c.find(M + "f")
        v = c.find(M + "v")
        if f is not None:
            return "formula", (f.text or "")
        if t == "inlineStr":
            is_ = c.find(M + "is")
            return "text", "".join(x.text or "" for x in is_.iter(M + "t")) if is_ is not None else ""
        if v is None or v.text is None:
            return "empty", None
        if t == "s":
            return "text", self.shared_strings()[int(v.text)]
        if t == "b":
            return "bool", v.text == "1"
        if t == "e":
            return "error", v.text
        if t == "str":
            return "text", v.text
        return "number", v.text

    def rows(self, name, first=1, last=None):
        """Yield (row_number, {col_letter: (kind, value)}) for non-empty cells."""
        root = self.sheet_root(name)
        sd = root.find(M + "sheetData")
        for row in sd:
            r = int(row.get("r"))
            if r < first or (last is not None and r > last):
                continue
            cells = {}
            for c in row:
                col, _ = split_ref(c.get("r"))
                kind, val = self.cell_value(c)
                if kind != "empty":
                    cells[col] = (kind, val)
            yield r, cells


TEMPLATE_NAME_HINTS = re.compile(r"^(template|vorlage|mod[eè]le|plantilla|modello|sjabloon|szablon|mall|"
                                 r"шаблон|テンプレート|قالب)", re.I)
