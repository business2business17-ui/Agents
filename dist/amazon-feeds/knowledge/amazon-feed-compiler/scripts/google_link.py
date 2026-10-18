#!/usr/bin/env python3
"""Open a Google Docs / Sheets / Slides / Drive link from the command line and save it as a local file.

Usage:
  google_link.py info  URL                                  parse the link (kind, id, tab) - no network
  google_link.py fetch URL [--format xlsx|csv|txt|docx|html|pdf|pptx|raw] [--gid N] [--out DIR] [--name NAME]
                           [--preview] [--max-mb 50] [--json]
  google_link.py peek  FILE                                 sheet names / dimensions of an .xlsx, rows of a .csv

What it does
  Google Sheet  -> xlsx (all tabs, default) or csv (one tab: --gid N, or the #gid=N / ?gid=N in the link)
  Google Doc    -> txt (default, best for agents), docx, html, pdf
  Google Slides -> pptx (default) or pdf
  Drive file    -> raw download (an uploaded .xlsx / .xlsm / .csv / .pdf / image is saved as it is)
  "Publish to the web" sheet links (/d/e/2PACX-.../pub) -> xlsx or csv

Access
  * Link shared as "Anyone with the link: Viewer"  -> works with no credentials.
  * Private file -> put an OAuth access token in the environment variable GOOGLE_ACCESS_TOKEN (scope drive.readonly is enough;
    e.g. from `gcloud auth application-default print-access-token`). The token is read from the environment ONLY: it is
    never written to disk, printed or sent to any host except Google's own. Short-lived: refresh when it expires.
  * In Claude with a Google Drive connector, prefer the connector for private files; this CLI is the portable fallback.
  * Read only: this tool never edits a Google file.

Safety
  Only https links on google.com / googleusercontent.com / googleapis.com are followed (no arbitrary URLs, no redirects to
  other hosts); sign-in pages are reported as "not shared", never followed; size cap --max-mb; the output name is sanitized.

IMPORTANT for Amazon feed templates: a feed template (.xlsm with macros, validations, hidden sheets) must be downloaded as the
ORIGINAL FILE from Drive (`--format raw` on a Drive file link). A native Google Sheet exported to xlsx has lost macros and Amazon's
validations: it is NOT a usable feed template (the agents stop with TEMPLATE_CORRUPTED / ask for the original).
Exit code 0 = saved, 1 = access/format problem (message says what to change), 2 = usage error.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ALLOWED_SUFFIXES = (".google.com", ".googleusercontent.com", ".googleapis.com")
LOGIN_HOSTS = ("accounts.google.com",)
ID_RE = re.compile(r"/d/(?:e/)?([A-Za-z0-9_-]{15,})")
EXT = {"xlsx": ".xlsx", "csv": ".csv", "txt": ".txt", "docx": ".docx", "html": ".html", "pdf": ".pdf", "pptx": ".pptx", "raw": ""}
DEFAULT_FORMAT = {"sheet": "xlsx", "sheet_pub": "xlsx", "doc": "txt", "slides": "pptx", "drive_file": "raw"}
TEST_BASE = os.environ.get("GOOGLE_LINK_TEST_BASE")  # test hook only: redirects all Google hosts to a local test server


class LinkError(Exception):
    pass


def host_ok(host):
    host = (host or "").lower()
    if TEST_BASE and host == urllib.parse.urlparse(TEST_BASE).hostname:
        return True
    return host == "google.com" or host.endswith(ALLOWED_SUFFIXES) or host == "googleapis.com"


def parse(url):
    u = urllib.parse.urlparse(url.strip())
    if u.scheme != "https" or not host_ok(u.hostname):
        raise LinkError("only https links on google.com / googleusercontent.com / googleapis.com are supported")
    q = urllib.parse.parse_qs(u.query)
    frag = urllib.parse.parse_qs(u.fragment)
    gid = (q.get("gid") or frag.get("gid") or [None])[0]
    path = u.path
    host = u.hostname.lower()
    fid = None
    m = ID_RE.search(path)
    if m:
        fid = m.group(1)
    elif q.get("id"):
        fid = q["id"][0]
    kind = None
    if host.startswith("docs.") and "/spreadsheets/" in path:
        kind = "sheet_pub" if "/d/e/" in path else "sheet"
    elif host.startswith("docs.") and "/document/" in path:
        kind = "doc"
    elif host.startswith("docs.") and "/presentation/" in path:
        kind = "slides"
    elif host.startswith("drive.") or host.startswith("drive.usercontent"):
        if "/folders/" in path:
            raise LinkError("folder links are not supported: send links to the individual files")
        kind = "drive_file"
    elif "/forms/" in path:
        raise LinkError("Google Forms are not supported")
    if not kind or not fid:
        raise LinkError("cannot recognise this Google link (need a Docs, Sheets, Slides or Drive file link)")
    return dict(kind=kind, id=fid, gid=gid, host=host, path=path, query=q)


def export_url(info, fmt, gid):
    base = TEST_BASE.rstrip("/") if TEST_BASE else None
    docs = base or "https://docs.google.com"
    drive = base or "https://drive.google.com"
    k, i = info["kind"], info["id"]
    if k == "sheet":
        if fmt == "csv":
            return f"{docs}/spreadsheets/d/{i}/export?format=csv" + (f"&gid={gid}" if gid else "")
        if fmt in ("xlsx", "pdf"):
            return f"{docs}/spreadsheets/d/{i}/export?format={fmt}"
    if k == "sheet_pub":
        out = "csv" if fmt == "csv" else "xlsx"
        return f"{docs}/spreadsheets/d/e/{i}/pub?output={out}" + (f"&gid={gid}" if gid and out == "csv" else "")
    if k == "doc" and fmt in ("txt", "docx", "html", "pdf"):
        return f"{docs}/document/d/{i}/export?format={fmt}"
    if k == "slides" and fmt in ("pptx", "pdf"):
        return f"{docs}/presentation/d/{i}/export/{fmt}"
    if k == "drive_file" and fmt == "raw":
        return f"{drive}/uc?export=download&id={i}"
    raise LinkError(f"format '{fmt}' is not available for a {k.replace('_', ' ')} (default: {DEFAULT_FORMAT[k]})")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def http_get(url, token, max_bytes, hops=6):
    for _ in range(hops):
        u = urllib.parse.urlparse(url)
        if u.hostname in LOGIN_HOSTS:
            raise LinkError("NOT_SHARED: Google asks for a sign-in. Set sharing to 'Anyone with the link: Viewer' or provide GOOGLE_ACCESS_TOKEN")
        if not host_ok(u.hostname):
            raise LinkError(f"redirect to a non-Google host refused: {u.hostname}")
        req = urllib.request.Request(url, headers={"User-Agent": "amazon-agents-google-link/1.0"})
        if token and (u.hostname.endswith("google.com") or u.hostname.endswith("googleapis.com") or TEST_BASE):
            req.add_header("Authorization", f"Bearer {token}")
        opener = urllib.request.build_opener(NoRedirect)
        try:
            resp = opener.open(req, timeout=60)
        except urllib.error.HTTPError as e:
            if e.code in (301, 302, 303, 307, 308):
                url = urllib.parse.urljoin(url, e.headers.get("Location", ""))
                continue
            if e.code in (401, 403):
                raise LinkError(f"HTTP {e.code}: no access. Share the file as 'Anyone with the link: Viewer' or provide a valid GOOGLE_ACCESS_TOKEN")
            if e.code == 404:
                raise LinkError("HTTP 404: file not found (wrong id, deleted, or not visible to this account)")
            if e.code == 429:
                raise LinkError("HTTP 429: Google rate limit, retry later")
            raise LinkError(f"HTTP {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            raise LinkError(f"network error: {e.reason} (is outbound access to Google allowed in this environment?)")
        with resp:
            ctype = resp.headers.get("Content-Type", "")
            data = resp.read(max_bytes + 1)
            if len(data) > max_bytes:
                raise LinkError(f"file larger than the {max_bytes // (1 << 20)} MB cap (use --max-mb)")
            return data, ctype, resp.headers.get("Content-Disposition", "")
    raise LinkError("too many redirects")


def looks_like_html(data, ctype, wanted):
    return wanted != "html" and ("text/html" in ctype.lower() or data[:200].lstrip().lower().startswith((b"<!doctype html", b"<html")))


def safe_name(s):
    s = re.sub(r"[^\w.\- ]+", "_", s, flags=re.UNICODE).strip(" .") or "google_file"
    return s[:120]


def fetch(a):
    info = parse(a.url)
    fmt = a.format or DEFAULT_FORMAT[info["kind"]]
    gid = a.gid or info["gid"]
    token = os.environ.get("GOOGLE_ACCESS_TOKEN") or None
    url = export_url(info, fmt, gid)
    cap = a.max_mb * (1 << 20)
    tried = [url]
    try:
        data, ctype, disp = http_get(url, token, cap)
    except LinkError as e:
        # an uploaded Office file opened in Sheets/Docs is not a native Google file: fall back to the Drive download
        if info["kind"] in ("sheet", "doc", "slides") and "HTTP 400" in str(e):
            url = export_url(dict(info, kind="drive_file"), "raw", None)
            tried.append(url)
            data, ctype, disp = http_get(url, token, cap)
            fmt = "raw"
        else:
            raise
    if looks_like_html(data, ctype, fmt):
        if info["kind"] == "drive_file" and b"confirm=" in data[:200000]:
            m = re.search(rb'confirm=([0-9A-Za-z_-]+)', data)
            url2 = f"https://drive.usercontent.google.com/download?id={info['id']}&export=download&confirm={m.group(1).decode() if m else 't'}"
            if TEST_BASE:
                url2 = f"{TEST_BASE.rstrip('/')}/uc?export=download&id={info['id']}&confirm=t"
            tried.append(url2)
            data, ctype, disp = http_get(url2, token, cap)
        if looks_like_html(data, ctype, fmt):
            raise LinkError("NOT_SHARED: Google returned a web page instead of the file (sign-in or permission page). "
                            "Share the file as 'Anyone with the link: Viewer' or provide GOOGLE_ACCESS_TOKEN")
    name = a.name
    if not name:
        m = re.search(r"filename\*?=(?:UTF-8'')?\"?([^\";]+)", disp or "")
        name = urllib.parse.unquote(m.group(1)) if m else f"google_{info['kind']}_{info['id'][:8]}"
    ext = EXT.get(fmt, "")
    if fmt == "raw" and not os.path.splitext(name)[1]:
        ext = {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx", "application/vnd.ms-excel.sheet.macroenabled.12": ".xlsm",
               "application/pdf": ".pdf", "text/csv": ".csv"}.get(ctype.split(";")[0].strip().lower(), "")
        if not ext and data[:2] == b"PK":
            ext = ".zip"
    if fmt == "csv" and gid:
        name = f"{os.path.splitext(name)[0]}_gid{gid}"
    name = safe_name(os.path.splitext(name)[0] if EXT.get(fmt) else name) + (ext if EXT.get(fmt) or ext else "")
    os.makedirs(a.out, exist_ok=True)
    path = os.path.join(a.out, name)
    n = 1
    while os.path.exists(path):  # never overwrite a previous download
        base, e2 = os.path.splitext(name)
        path = os.path.join(a.out, f"{base}_{n}{e2}")
        n += 1
    with open(path, "wb") as f:
        f.write(data)
    res = dict(source_url=f"https://{info['host']}{info['path']}", kind=info["kind"], file_id=info["id"], gid=gid, format=fmt,
               path=path, bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), origin="GOOGLE_LINK",
               fetched_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), authenticated=bool(token))
    warnings = []
    if info["kind"] in ("sheet", "sheet_pub") and fmt == "xlsx":
        warnings.append("native Google Sheet exported to xlsx: macros, Amazon validations and hidden structures are NOT preserved - "
                        "do not use this file as an Amazon feed template (download the original .xlsm from Drive with a Drive file link)")
    if info["kind"] == "sheet" and fmt == "csv" and not gid:
        warnings.append("csv contains only the first tab; pass --gid N (or a link with #gid=N) for another tab, or use xlsx for all tabs")
    if warnings:
        res["warnings"] = warnings
    return res


def peek(path):
    low = path.lower()
    if low.endswith((".xlsx", ".xlsm")):
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        for ws in wb.worksheets:
            try:
                dims = ws.calculate_dimension()
            except Exception:  # noqa: BLE001
                dims = "?"
            print(f"sheet '{ws.title}' state={ws.sheet_state} dims={dims}")
            for i, row in enumerate(ws.iter_rows(values_only=True)):
                if i >= 3:
                    break
                print("   ", [c for c in row[:10]])
    elif low.endswith(".csv"):
        with open(path, encoding="utf-8-sig", errors="replace") as f:
            lines = f.read().splitlines()
        print(f"{len(lines)} lines")
        for l in lines[:3]:
            print("   ", l[:200])
    else:
        print(f"{os.path.getsize(path)} bytes")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    pi = sub.add_parser("info")
    pi.add_argument("url")
    pf = sub.add_parser("fetch")
    pf.add_argument("url")
    pf.add_argument("--format", choices=sorted(EXT))
    pf.add_argument("--gid")
    pf.add_argument("--out", default="downloads")
    pf.add_argument("--name")
    pf.add_argument("--max-mb", type=int, default=50)
    pf.add_argument("--preview", action="store_true")
    pf.add_argument("--json", action="store_true")
    pk = sub.add_parser("peek")
    pk.add_argument("file")
    a = ap.parse_args()
    try:
        if a.cmd == "info":
            info = parse(a.url)
            info.pop("query")
            info["default_format"] = DEFAULT_FORMAT[info["kind"]]
            print(json.dumps(info, indent=2))
            return 0
        if a.cmd == "peek":
            peek(a.file)
            return 0
        res = fetch(a)
    except LinkError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(f"saved {res['path']} ({res['bytes']} bytes, sha256 {res['sha256'][:12]}..., {res['kind']} -> {res['format']})")
        for w in res.get("warnings", []):
            print("WARNING:", w)
    if a.preview:
        peek(res["path"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
