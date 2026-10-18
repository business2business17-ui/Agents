#!/usr/bin/env python3
"""Deterministic listing-content checks from the Agent 1 spec (sections 29-37, 13-16, 103).

Usage:
  content_check.py --file content.json [--competitors "Nike,Adidas"] [--verified-claims "waterproof,IPX4"]
  content_check.py --file handoff.jsonl           (reads record["content"], one JSON object per line)
  content_check.py --title "..." --backend "..." [--lang de]
Languages: built-in prohibited-term / claim lists exist for en, de, fr, es, it only. For any other content language
(pl, nl, sv, pt, tr, ja, ar, hi ...) the AGENT must translate the English lists (best, #1, guaranteed, cure, FDA approved,
medically proven, cheapest, lowest price, miracle, free shipping + the strict-claim list) into that language and pass them with
--forbidden-extra "a,b,c" / --claims-extra "..." or --forbidden-file file.txt (one term per line). Without them a
LOCALE_LIST_MISSING warning is reported: a clean result is then NOT proof that the copy is compliant.
Limits come from content_limits.json (USER_SUPPLIED 2026-10-11; Product Type rule always wins), chosen per marketplace:
  title 75 chars (media 200 with --category media), item highlights 125, bullets 5 x 10-255 chars (~1000 bytes indexed in total),
  description 2000 chars plain text, backend bytes 249 (JP 500, IN 200). Override with --title-max / --highlights-max /
  --bullets-max / --backend-max-bytes / --max-word-repeat / --bullet-max-chars; pass --marketplace XX (or a record "marketplace").
Checks: title length / repeated meaningful words / ALL CAPS beyond the brand (--brand) / promo phrases / prohibited elements (price,
shipping, URL, e-mail, phone, emoji, excessive punctuation) / forbidden terms / competitor brands / unverified regulated claims /
item highlights: length, own repetition, ANY word already used in the title / bullets: unique, 10-255 chars, symbols, end punctuation,
indexed bytes / description: 2000 chars, no HTML / backend: byte length per marketplace, commas, duplicates, title words.
Findings: ERROR blocks READY_TO_PUBLISH, WARN needs a human look. Exit 0 = no ERROR, 1 = at least one ERROR.
Heuristic by design: the agent still reads the copy. Product-Type-specific limits always win over these defaults.
"""
import argparse
import json
import re
import sys
import unicodedata
import os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
try:
    LIM = json.load(open(os.path.join(HERE, "content_limits.json"), encoding="utf-8"))
except (OSError, ValueError):  # pragma: no cover - fallback keeps the tool usable without the file
    LIM = {}
BULLET_SYMBOLS = re.compile("[\u2713\u2714\u2705\u2611\u2022\u25CF\u25AA\u25B6\u2605\u2606*\u27A4\u2192]")
HTML_TAG = re.compile(r"</?(?!br\s*/?>)[a-z][^>]*>", re.I)


def limit(path, default):
    cur = LIM
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def backend_limit(marketplace):
    table = limit(("backend", "max_bytes"), {"default": 249})
    return table.get((marketplace or "").upper(), table.get("default", 249))

FORBIDDEN = ["best", "#1", "no.1", "number one", "guaranteed", "guarantee", "cure", "cures", "fda approved",
             "medically proven", "cheapest", "lowest price", "miracle", "free shipping", "sale", "discount",
             # light localisation of the same ideas
             "beste", "bester", "bestes", "garantiert", "heilt", "wunder", "günstigster", "gratis versand",
             "meilleur", "garanti", "guéri", "miracle", "moins cher", "livraison gratuite",
             "mejor", "garantizado", "cura", "milagro", "más barato", "envío gratis",
             "migliore", "garantito", "guarisce", "miracolo", "più economico", "spedizione gratuita"]
STRICT_CLAIMS = ["waterproof", "water resistant", "water-resistant", "clinical", "clinically", "medical", "therapeutic",
                 "antibacterial", "antimicrobial", "organic", "natural", "vegan", "cruelty-free", "cruelty free",
                 "hypoallergenic", "bpa-free", "bpa free", "non-toxic", "safe for children", "dermatologist",
                 "professional grade", "pregnancy safe", "certified", "eco-friendly", "sustainable",
                 "wasserdicht", "klinisch", "bio", "vegan", "hypoallergen", "zertifiziert", "nachhaltig",
                 "étanche", "cliniquement", "biologique", "certifié", "écologique",
                 "impermeable", "clínicamente", "ecológico", "certificado", "impermeabile", "certificato"]
STOP = set("""a an the and or of for to with in on at by from as is are be this that it its your you
der die das und oder von für mit in auf bei aus als ist sind ein eine einer zu
le la les un une et ou de du des pour avec sur par en
el los las un una y o de del para con en por
il lo gli i e o di del per con su da un uno una""".split())
BUILTIN_LANGS = {"en", "de", "fr", "es", "it"}
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐✅❌]")
URL = re.compile(r"(https?://|www\.)\S+", re.I)
MAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
PHONE = re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{8,}\d)(?!\d)")
PRICE = re.compile(r"([€$£¥]\s?\d|\d\s?[€$£¥]|\b\d+([.,]\d+)?\s?(eur|usd|gbp|euro|dollar)\b|\b\d+\s?%\s?(off|rabatt|reduc|dto|sconto))", re.I)


def norm_token(w):
    w = unicodedata.normalize("NFKC", w.lower())
    for suf in ("ies", "es", "s"):
        if len(w) > 4 and w.endswith(suf):
            return w[: -len(suf)] + ("y" if suf == "ies" else "")
    return w


def tokens(text):
    return [t for t in re.findall(r"[\w'-]+", text.lower(), re.UNICODE)]


def meaningful(text):
    return [norm_token(t) for t in tokens(text) if t not in STOP and not t.isdigit() and len(t) > 1]


def f(sev, field, code, msg):
    return dict(severity=sev, field=field, code=code, message=msg)


def find_terms(text, terms):
    low = text.lower()
    hits = []
    for t in terms:
        pat = r"(?<!\w)" + re.escape(t.lower()) + r"(?!\w)" if t[0].isalnum() else re.escape(t.lower())
        if re.search(pat, low):
            hits.append(t)
    return hits


def check(c, o):
    out = []
    title = (c.get("title") or "").strip()
    hi = (c.get("item_highlights") or "").strip()
    bullets = [b.strip() for b in (c.get("bullet_points") or []) if b and b.strip()]
    desc = (c.get("description") or "").strip()
    backend = (c.get("backend_search_terms") or "").strip()

    if not title:
        out.append(f("ERROR", "title", "TITLE_MISSING", "title is empty"))
    else:
        tmax = o.title_max or (limit(("title", "media_max_chars"), 200) if (o.category or "").lower() == "media" else limit(("title", "max_chars"), 75))
        if len(title) > tmax:
            out.append(f("ERROR", "title", "TITLE_TOO_LONG", f"{len(title)} chars > {tmax} (Amazon may shorten or rewrite over-limit titles; Product Type rule may differ)"))
        low_t = title.lower()
        for ph in limit(("title", "promo_phrases"), ["free shipping", "best seller"]):
            if ph in low_t:
                out.append(f("ERROR", "title", "TITLE_PROMO_PHRASE", f"promotional phrase '{ph}'"))
        brand_words = {w.lower() for w in re.findall(r"\w+", o.brand or "")}
        caps = [w for w in re.findall(r"[^\W\d_]{4,}", title) if w.isupper() and w.lower() not in brand_words]
        if caps:
            out.append(f("WARN", "title", "TITLE_CAPS_WORDS", f"ALL CAPS words other than the brand: {caps[:6]}"))
        cnt = Counter(meaningful(title))
        rep = {w: n for w, n in cnt.items() if n > (o.max_word_repeat or limit(("title", "max_word_repeat"), 2))}
        if rep:
            out.append(f("ERROR", "title", "TITLE_WORD_REPETITION", f"words used more than {o.max_word_repeat or limit(('title', 'max_word_repeat'), 2)}x: {rep}"))
        if PRICE.search(title):
            out.append(f("ERROR", "title", "TITLE_PRICE_OR_DISCOUNT", "price/discount text in title"))
        for rx, code in ((URL, "URL"), (MAIL, "EMAIL"), (PHONE, "PHONE"), (EMOJI, "EMOJI")):
            if rx.search(title):
                out.append(f("ERROR", "title", f"TITLE_{code}", f"{code.lower()} in title"))
        if re.search(r"[!?]{2,}|[*~^<>{}]|\.{4,}|(?:\s[-/|]\s){2,}", title):
            out.append(f("WARN", "title", "TITLE_PUNCTUATION", "excessive punctuation / decorative symbols"))
        if title.isupper() and len(title) > 8:
            out.append(f("WARN", "title", "TITLE_ALL_CAPS", "all caps title"))
    if hi:
        hmax = o.highlights_max or limit(("item_highlights", "max_chars"), 125)
        if len(hi) > hmax:
            out.append(f("ERROR", "item_highlights", "HIGHLIGHTS_TOO_LONG", f"{len(hi)} chars > {hmax}"))
        hrep = {w: n for w, n in Counter(meaningful(hi)).items() if n > (o.max_word_repeat or limit(("item_highlights", "max_word_repeat"), 2))}
        if hrep:
            out.append(f("ERROR", "item_highlights", "HIGHLIGHTS_WORD_REPETITION", f"words repeated inside the field: {hrep}"))
        if title and hi.lower() == title.lower():
            out.append(f("ERROR", "item_highlights", "HIGHLIGHTS_COPY_OF_TITLE", "identical to title"))
        elif title:
            hw, tw = set(meaningful(hi)), set(meaningful(title))
            shared = sorted(hw & tw)
            if shared and len(shared) / max(1, len(hw)) > 0.5:
                out.append(f("ERROR", "item_highlights", "HIGHLIGHTS_REPEAT_TITLE", f"{len(shared)}/{len(hw)} highlight words already in the title: {shared[:10]}"))
            elif shared:
                out.append(f("WARN", "item_highlights", "HIGHLIGHTS_SHARE_TITLE_WORDS", f"words already indexed from the title (no extra weight, wastes space): {shared[:10]}"))
        if title and len(title) >= limit(("title", "max_chars"), 75):
            out.append(f("WARN", "item_highlights", "HIGHLIGHTS_NOT_SHOWN", "Item Highlight is displayed only when the item name is under 75 characters"))
    if len(bullets) > o.bullets_max:
        out.append(f("ERROR", "bullet_points", "TOO_MANY_BULLETS", f"{len(bullets)} > {o.bullets_max} (unless the Product Type allows more)"))
    seen = set()
    bmin, bmax = limit(("bullets", "min_chars"), 10), o.bullet_max_chars or limit(("bullets", "max_chars"), 255)
    for i, b in enumerate(bullets, 1):
        k = re.sub(r"\W+", " ", b.lower()).strip()
        if k in seen:
            out.append(f("ERROR", f"bullet_{i}", "BULLET_DUPLICATE", "duplicates another bullet"))
        seen.add(k)
        if len(b) > bmax:
            out.append(f("ERROR", f"bullet_{i}", "BULLET_TOO_LONG", f"{len(b)} chars > {bmax} (some Product Types allow up to 500: check the template)"))
        if len(b) < bmin:
            out.append(f("ERROR", f"bullet_{i}", "BULLET_TOO_SHORT", f"{len(b)} chars < {bmin}"))
        if EMOJI.search(b) or BULLET_SYMBOLS.search(b):
            out.append(f("ERROR", f"bullet_{i}", "BULLET_SYMBOLS", "emoji, check mark, bullet or asterisk symbol in text"))
        if re.search(r"[.!?;:,]$", b):
            out.append(f("WARN", f"bullet_{i}", "BULLET_END_PUNCTUATION", "no punctuation at the end of a bullet"))
    ibytes = sum(len(b.encode("utf-8")) for b in bullets)
    if ibytes > limit(("bullets", "indexed_total_bytes"), 1000):
        out.append(f("WARN", "bullet_points", "BULLETS_INDEX_OVERFLOW", f"{ibytes} bytes in total; only about {limit(('bullets', 'indexed_total_bytes'), 1000)} are indexed for search, put key terms first"))
    if not desc:
        out.append(f("WARN", "description", "DESCRIPTION_MISSING", "description is empty"))
    else:
        dmax = limit(("description", "max_chars"), 2000)
        if len(desc) > dmax:
            out.append(f("ERROR", "description", "DESCRIPTION_TOO_LONG", f"{len(desc)} chars > {dmax}"))
        if HTML_TAG.search(desc):
            out.append(f("ERROR", "description", "DESCRIPTION_HTML", "HTML tags are not supported (plain text; a line-break tag is the only tolerated exception)"))
    if backend:
        nbytes = len(backend.encode("utf-8"))
        bmax_bytes = o.backend_max_bytes or backend_limit(o.marketplace)
        if nbytes > bmax_bytes:
            out.append(f("ERROR", "backend_search_terms", "BACKEND_TOO_LONG", f"{nbytes} bytes > {bmax_bytes} for {o.marketplace or 'default'} (bytes, not characters: non-ASCII letters take 2-4 bytes; over the limit Amazon ignores the whole field)"))
        if o.marketplace and o.marketplace.upper() not in limit(("backend", "confirmed_for"), []):
            out.append(f("WARN", "backend_search_terms", "BACKEND_LIMIT_UNCONFIRMED", f"byte limit for {o.marketplace} not confirmed (default {bmax_bytes} used): check Seller Central"))
        words = tokens(backend)
        dup = [w for w, n in Counter(words).items() if n > 1]
        if dup:
            out.append(f("WARN", "backend_search_terms", "BACKEND_DUPLICATE_WORDS", f"repeated: {dup[:10]}"))
        in_title = [w for w in set(words) if w in set(tokens(title)) and w not in STOP]
        if len(in_title) > 3:
            out.append(f("WARN", "backend_search_terms", "BACKEND_REPEATS_TITLE", f"already visible in title: {in_title[:10]}"))
        if re.search(r"\bB0[A-Z0-9]{8}\b", backend):
            out.append(f("ERROR", "backend_search_terms", "BACKEND_ASIN", "ASIN in search terms"))
        if "," in backend:
            out.append(f("ERROR", "backend_search_terms", "BACKEND_COMMAS", "commas are not allowed; separate terms by spaces"))
    comps = [x.strip() for x in (o.competitors or "").split(",") if x.strip()]
    verified = [x.strip().lower() for x in (o.verified_claims or "").split(",") if x.strip()]
    fields = {"title": title, "item_highlights": hi, "description": desc, "backend_search_terms": backend}
    fields.update({f"bullet_{i}": b for i, b in enumerate(bullets, 1)})
    extra_f = [x.strip() for x in (o.forbidden_extra or "").split(",") if x.strip()]
    if o.forbidden_file:
        extra_f += [l.strip() for l in open(o.forbidden_file, encoding="utf-8-sig") if l.strip()]
    extra_c = [x.strip() for x in (o.claims_extra or "").split(",") if x.strip()]
    lang = (o.lang or c.get("language") or "").lower()
    if lang and lang not in BUILTIN_LANGS and not (extra_f and extra_c):
        out.append(f("WARN", "content", "LOCALE_LIST_MISSING",
                     f"no built-in prohibited-term/claim lists for language '{lang}': translate them and pass --forbidden-extra/--claims-extra "
                     "(a clean result is not proof of compliance)"))
    for name, text in fields.items():
        if not text:
            continue
        for t in find_terms(text, FORBIDDEN + extra_f):
            out.append(f("ERROR", name, "FORBIDDEN_TERM_FOUND", f"'{t}' (prohibited promotional/medical wording)"))
        for t in find_terms(text, comps):
            out.append(f("ERROR", name, "COMPETITOR_BRAND", f"'{t}'"))
        for t in find_terms(text, STRICT_CLAIMS + extra_c):
            if not any(v and (v in t.lower() or t.lower() in v) for v in verified):
                out.append(f("WARN", name, "CLAIM_NEEDS_EVIDENCE", f"'{t}' is a strictly verified claim: needs evidence in the Evidence Matrix"))
    return out


def load_records(path):
    txt = open(path, encoding="utf-8-sig").read()
    if path.endswith(".jsonl"):
        return [json.loads(l) for l in txt.splitlines() if l.strip()]
    data = json.loads(txt)
    return data if isinstance(data, list) else [data]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file")
    ap.add_argument("--title")
    ap.add_argument("--highlights")
    ap.add_argument("--backend")
    ap.add_argument("--lang")
    ap.add_argument("--forbidden-extra", default="", help="localized prohibited terms for the content language, comma-separated")
    ap.add_argument("--claims-extra", default="", help="localized strictly-verified claim terms, comma-separated")
    ap.add_argument("--forbidden-file", help="file with extra prohibited terms, one per line")
    ap.add_argument("--competitors", default="")
    ap.add_argument("--verified-claims", default="")
    ap.add_argument("--title-max", type=int, default=0, help="override; 0 = content_limits.json")
    ap.add_argument("--highlights-max", type=int, default=0)
    ap.add_argument("--bullets-max", type=int, default=5)
    ap.add_argument("--bullet-max-chars", type=int, default=0)
    ap.add_argument("--backend-max-bytes", type=int, default=0)
    ap.add_argument("--max-word-repeat", type=int, default=0)
    ap.add_argument("--marketplace", default="", help="DE, UK, JP ... (backend byte limit differs per marketplace)")
    ap.add_argument("--category", default="", help="'media' keeps the 200-char title limit")
    ap.add_argument("--brand", default="", help="brand name; the only text allowed in ALL CAPS")
    ap.add_argument("--json", action="store_true")
    o = ap.parse_args()
    o.marketplace_arg, o.brand_arg = o.marketplace, o.brand
    if o.file:
        recs = load_records(o.file)
    elif o.title or o.backend:
        recs = [dict(title=o.title, item_highlights=o.highlights, backend_search_terms=o.backend)]
    else:
        ap.error("give --file or --title/--backend")
    results, errors = [], 0
    for i, r in enumerate(recs, 1):
        c = r.get("content", r)
        o.marketplace = r.get("marketplace") or c.get("marketplace") or o.marketplace_arg
        o.brand = r.get("brand") or c.get("brand") or o.brand_arg
        findings = check(c, o)
        errors += sum(x["severity"] == "ERROR" for x in findings)
        results.append(dict(record=r.get("sku") or r.get("internal_product_id") or i,
                            marketplace=r.get("marketplace"), findings=findings))
    if o.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for r in results:
            print(f"[{r['record']}] {r['marketplace'] or ''}")
            for x in r["findings"] or [dict(severity="OK", field="-", code="-", message="no findings")]:
                print(f"  {x['severity']:5} {x['field']:22} {x['code']:26} {x['message']}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
