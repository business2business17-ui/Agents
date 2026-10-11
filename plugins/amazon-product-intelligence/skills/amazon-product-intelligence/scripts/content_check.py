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
Limits (defaults from the spec; override when the Product Type rule differs):
  --title-max 75  --highlights-max 125  --bullets-max 5  --backend-max-bytes 249  --max-word-repeat 2
Checks: title length / repeated meaningful words / prohibited elements (price, shipping, URL, e-mail, phone, emoji,
excessive punctuation) / forbidden terms / competitor brands / unverified regulated claims / highlights not a
copy of the title / unique bullets / backend byte length and duplicates of title words.
Findings: ERROR blocks READY_TO_PUBLISH, WARN needs a human look. Exit 0 = no ERROR, 1 = at least one ERROR.
Heuristic by design: the agent still reads the copy. Product-Type-specific limits always win over these defaults.
"""
import argparse
import json
import re
import sys
import unicodedata
from collections import Counter

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
        if len(title) > o.title_max:
            out.append(f("ERROR", "title", "TITLE_TOO_LONG", f"{len(title)} chars > {o.title_max} (Product Type rule may differ)"))
        cnt = Counter(meaningful(title))
        rep = {w: n for w, n in cnt.items() if n > o.max_word_repeat}
        if rep:
            out.append(f("ERROR", "title", "TITLE_WORD_REPETITION", f"words used more than {o.max_word_repeat}x: {rep}"))
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
        if len(hi) > o.highlights_max:
            out.append(f("ERROR", "item_highlights", "HIGHLIGHTS_TOO_LONG", f"{len(hi)} chars > {o.highlights_max}"))
        if title and hi.lower() == title.lower():
            out.append(f("ERROR", "item_highlights", "HIGHLIGHTS_COPY_OF_TITLE", "identical to title"))
        elif title and len(set(meaningful(hi)) & set(meaningful(title))) / max(1, len(set(meaningful(hi)))) > 0.8:
            out.append(f("WARN", "item_highlights", "HIGHLIGHTS_REPEAT_TITLE", ">80% of highlight words already in title"))
    if len(bullets) > o.bullets_max:
        out.append(f("ERROR", "bullet_points", "TOO_MANY_BULLETS", f"{len(bullets)} > {o.bullets_max} (unless the Product Type allows more)"))
    seen = set()
    for i, b in enumerate(bullets, 1):
        k = re.sub(r"\W+", " ", b.lower()).strip()
        if k in seen:
            out.append(f("ERROR", f"bullet_{i}", "BULLET_DUPLICATE", "duplicates another bullet"))
        seen.add(k)
        if len(b) > 500:
            out.append(f("WARN", f"bullet_{i}", "BULLET_LONG", f"{len(b)} chars; check the Product Type limit"))
    if not desc:
        out.append(f("WARN", "description", "DESCRIPTION_MISSING", "description is empty"))
    if backend:
        nbytes = len(backend.encode("utf-8"))
        if nbytes > o.backend_max_bytes:
            out.append(f("ERROR", "backend_search_terms", "BACKEND_TOO_LONG", f"{nbytes} bytes > {o.backend_max_bytes}"))
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
            out.append(f("WARN", "backend_search_terms", "BACKEND_COMMAS", "commas are wasted bytes; separate by spaces"))
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
    ap.add_argument("--title-max", type=int, default=75)
    ap.add_argument("--highlights-max", type=int, default=125)
    ap.add_argument("--bullets-max", type=int, default=5)
    ap.add_argument("--backend-max-bytes", type=int, default=249)
    ap.add_argument("--max-word-repeat", type=int, default=2)
    ap.add_argument("--json", action="store_true")
    o = ap.parse_args()
    if o.file:
        recs = load_records(o.file)
    elif o.title or o.backend:
        recs = [dict(title=o.title, item_highlights=o.highlights, backend_search_terms=o.backend)]
    else:
        ap.error("give --file or --title/--backend")
    results, errors = [], 0
    for i, r in enumerate(recs, 1):
        c = r.get("content", r)
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
