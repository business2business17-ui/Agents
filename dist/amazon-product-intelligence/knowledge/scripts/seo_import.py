#!/usr/bin/env python3
"""Normalize and sanitize SEO keyword data: Helium 10 Cerebro / Magnet exports (CSV, XLSX) or Helium 10 MCP results.

Implements spec sections 25-28 (SEO engine, tiers, marketplace isolation, sanitization report). SEO data is DEMAND only:
nothing here proves a product fact.

Usage:
  seo_import.py FILE [FILE ...] --marketplace DE --product-terms "handyhülle,hülle,pixel 8"
        [--competitors "samsung,apple"] [--verified-claims "wasserdicht"] [--exclude-terms "gebraucht"]
        [--seo-date 2026-10-01] [--max-age-days N] [--top1 5] [--top2 15] [--sku SKU-1]
        [--out seo.json] [--xlsx seo.xlsx]

FILE may be: a Cerebro/Magnet CSV/XLSX export, or JSON / JSON.GZ / CSV saved from Helium 10 MCP tools
(get_keywords_by_asin = Cerebro, get_keywords_by_keyword = Magnet, search_amazon_keywords, analyze_keywords,
find_keywords_with_multi_source). Several files of the same marketplace are merged (best search volume kept).

What it does
  * maps columns by synonyms (EN/DE/FR/IT/ES/PL headers; unknown columns are kept untouched)
  * flags SEO_MARKETPLACE_MISMATCH when the keyword language does not fit the target marketplace
    (a US export is never "translated" into another market's SEO) and SEO_SOURCE_OLD when --max-age-days is given
  * removes exact duplicates, groups semantic duplicates (same words, any order, plurals)
  * excludes competitor brands, prohibited/medical terms, regulated claims without evidence, irrelevant phrases
  * relevance needs --product-terms (from TTX / product type). Without them nothing is tiered (NEEDS_PRODUCT_TERMS)
  * tiers TIER_1_PRIMARY / TIER_2_SECONDARY (head terms, <= 3 words) / TIER_3_LONG_TAIL (>= 4 words) / TIER_4_SEMANTIC / EXCLUDE;
    suggested placement
  * prints the SEO Sanitization Report (counts) required before content generation
Heuristic by design: tier counts (top1/top2) are tunable configuration, not Amazon rules. The agent reviews the result.
Exit 0 = ok, 1 = marketplace mismatch / no usable keywords / old source (needs a human decision), 2 = usage error.
"""
import argparse
import csv
import gzip
import io
import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import date, datetime

from content_check import FORBIDDEN, STRICT_CLAIMS, STOP, find_terms, meaningful, norm_token, tokens

SYN = {
    "keyword": ["keyword phrase", "keyword", "keywords", "phrase", "search term", "search query", "suchbegriff", "suchanfrage",
                "mot cle", "mot clé", "parola chiave", "palabra clave", "fraza kluczowa", "keywords phrase"],
    "search_volume": ["search volume", "current search volume", "exact search volume", "monthly search volume", "sv",
                      "suchvolumen", "volume de recherche", "volume di ricerca", "volumen de busqueda", "wolumen wyszukiwań"],
    "iq_score": ["cerebro iq score", "magnet iq score", "iq score", "iq", "cerebro iq"],
    "competing_products": ["competing products", "results number", "results", "competing_products", "wettbewerbsprodukte"],
    "cpr": ["cpr", "cerebro product rank", "giveaways"],
    "title_density": ["title density", "exact title match products count", "titeldichte"],
    "keyword_sales": ["keyword sales", "keyword_sales"],
    "organic_rank": ["organic rank", "organischer rang"],
    "sponsored_rank": ["sponsored rank", "gesponserter rang"],
    "amazon_recommended": ["amazon recommended", "amazon empfohlen"],
    "trend": ["search volume trend", "sv trend", "trend"],
    "cpc": ["cpc", "suggested ppc bid", "cost per click", "ppc bid"],
    "marketplace": ["marketplace", "country", "store", "marktplatz", "pays"],
}
LANG_MARKERS = {
    "en": "for with the and women men case cover phone kids girls boys set of black white blue for-men".split(),
    "de": "für mit und der die das herren damen hülle handyhülle schutzhülle kinder mädchen jungen set aus schwarz weiß".split(),
    "fr": "pour avec et le la les de femme homme coque étui enfant fille garçon ensemble noir blanc".split(),
    "it": "per con e il lo la di donna uomo custodia cover bambini ragazza ragazzo nero bianco".split(),
    "es": "para con y el la los de mujer hombre funda carcasa niños niña niño negro blanco".split(),
    "nl": "voor met en de het van dames heren hoesje kinderen meisjes jongens zwart wit".split(),
    "pl": "dla z i na do etui męskie damskie dzieci czarny biały pokrowiec".split(),
    "sv": "för med och till fodral barn flickor pojkar svart vit skal".split(),
    "pt": "para com e o a de mulher homem capa crianças preto branco".split(),
    "tr": "için ve ile kılıf kapak erkek kadın çocuk siyah beyaz".split(),
}
EXPECTED = {"US": ["en"], "UK": ["en"], "CA": ["en", "fr"], "AU": ["en"], "IN": ["en"], "IE": ["en"], "SG": ["en"], "AE": ["en"],
            "SA": ["en"], "EG": ["en"], "DE": ["de"], "FR": ["fr"], "IT": ["it"], "ES": ["es"], "MX": ["es"], "NL": ["nl"],
            "BE": ["nl", "fr"], "PL": ["pl"], "SE": ["sv"], "BR": ["pt"], "TR": ["tr"], "JP": ["ja"]}
CORE_LANG_TOKENS = {k: set(v) for k, v in LANG_MARKERS.items()}
TIER_PLACEMENT = {"TIER_1_PRIMARY": "title", "TIER_2_SECONDARY": "highlights/bullets", "TIER_3_LONG_TAIL": "bullets/description",
                  "TIER_4_SEMANTIC": "backend search terms", "EXCLUDE": "-"}


def keyn(s):
    s = unicodedata.normalize("NFKC", str(s)).lower()
    return re.sub(r"[^0-9a-zà-ÿąćęłńóśźż]+", " ", s).strip()


def num(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(" ", "").replace(" ", "")
    if s in ("", "-", "—", "n/a", "N/A", "null", "None"):
        return None
    s = s.rstrip("%")
    if "," in s and "." in s:
        s = s.replace(",", "") if s.rfind(".") > s.rfind(",") else s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", "") if re.fullmatch(r"-?\d{1,3}(,\d{3})+", s) else s.replace(",", ".")
    elif "." in s and re.fullmatch(r"-?\d{1,3}(\.\d{3})+", s):
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return None


def map_columns(header):
    out = {}
    norm = {h: keyn(h) for h in header if h is not None}
    for field, syns in SYN.items():
        sn = {keyn(x) for x in syns}
        for h, n in norm.items():
            if n in sn and field not in out:
                out[field] = h
    return out


def read_rows(path):
    low = path.lower()
    raw = open(path, "rb").read()
    if low.endswith(".gz"):
        raw = gzip.decompress(raw)
        low = low[:-3]
    if low.endswith(".json"):
        d = json.loads(raw.decode("utf-8-sig"))
        if isinstance(d, dict):
            for k in ("rows", "keywords", "items", "results"):
                if isinstance(d.get(k), list):
                    d = d[k]
                    break
            else:
                data = d.get("data")
                if isinstance(data, dict):
                    d = next((data[k] for k in ("rows", "keywords", "items", "results") if isinstance(data.get(k), list)), [])
                elif isinstance(data, list):
                    d = data
        if not isinstance(d, list):
            sys.exit(f"{path}: cannot find a list of keyword rows in the JSON")
        return [{(k.replace("_", " ") if isinstance(k, str) else k): v for k, v in r.items()} for r in d if isinstance(r, dict)]
    if low.endswith((".xlsx", ".xlsm")):
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb[wb.sheetnames[0]]
        it = ws.iter_rows(values_only=True)
        header = next(it)
        return [dict(zip(header, r)) for r in it if any(c is not None for c in r)]
    text = raw.decode("utf-8-sig", errors="replace")
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    return list(csv.DictReader(io.StringIO(text), dialect=dialect))


def detect_language(keywords):
    sample = keywords[:300]
    votes = Counter()
    for k in sample:
        tk = set(tokens(k))
        for lang, marks in CORE_LANG_TOKENS.items():
            if tk & marks:
                votes[lang] += 1
    n = max(1, len(sample))
    return {l: round(c / n, 3) for l, c in votes.most_common()}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--marketplace", required=True)
    ap.add_argument("--product-terms", default="", help="comma-separated product-type / model / key attribute terms from the verified TTX")
    ap.add_argument("--competitors", default="")
    ap.add_argument("--verified-claims", default="")
    ap.add_argument("--exclude-terms", default="")
    ap.add_argument("--seo-date")
    ap.add_argument("--max-age-days", type=int)
    ap.add_argument("--top1", type=int, default=5)
    ap.add_argument("--top2", type=int, default=15)
    ap.add_argument("--min-sv", type=float, default=0, help="minimum search volume for T1-T3 (0 = any positive)")
    ap.add_argument("--sku", default="")
    ap.add_argument("--out")
    ap.add_argument("--xlsx")
    a = ap.parse_args()
    mp = a.marketplace.upper()

    rows, col_maps, src = [], [], []
    for f in a.files:
        r = read_rows(f)
        if not r:
            sys.exit(f"{f}: no rows")
        cm = map_columns(list(r[0].keys()))
        if "keyword" not in cm:
            sys.exit(f"{f}: no keyword column recognised in headers {list(r[0].keys())[:12]}")
        col_maps.append(cm)
        src.append(dict(file=os.path.basename(f), rows=len(r), mapped_columns=cm,
                        unmapped_columns=[h for h in r[0].keys() if h not in cm.values()][:30]))
        for x in r:
            rec = {fld: x.get(h) for fld, h in cm.items()}
            rec["_src"] = os.path.basename(f)
            rows.append(rec)

    flags = []
    if a.seo_date:
        seo_date, date_basis = a.seo_date, "stated by the user"
    else:
        seo_date = datetime.fromtimestamp(max(os.path.getmtime(f) for f in a.files)).date().isoformat()
        date_basis = "file modification time (NOT the data date: ask the user for the export date)"
    if a.max_age_days is not None:
        age = (date.today() - date.fromisoformat(seo_date)).days
        if age > a.max_age_days:
            flags.append(dict(code="SEO_SOURCE_OLD", detail=f"{age} days old > {a.max_age_days}"))

    mcols = [r.get("marketplace") for r in rows if r.get("marketplace")]
    if mcols:
        seen = {str(m).strip().upper() for m in mcols}
        if not any(mp == s or s.endswith(mp) or mp in s for s in seen):
            flags.append(dict(code="SEO_MARKETPLACE_MISMATCH", detail=f"file says {sorted(seen)[:5]}, target {mp}"))
    shares = detect_language([str(r["keyword"]) for r in sorted(rows, key=lambda r: -(num(r.get("search_volume")) or 0))
                              if r.get("keyword")])
    exp = EXPECTED.get(mp, [])
    if exp and shares:
        top_lang, top_share = next(iter(shares.items()))
        exp_share = max(shares.get(l, 0) for l in exp)
        # english tokens are common in every market, so only flag a clearly different dominant language
        if top_lang not in exp and top_share >= 0.4 and exp_share < 0.15:
            flags.append(dict(code="SEO_MARKETPLACE_MISMATCH", detail=f"keywords look {top_lang} ({top_share:.0%}), "
                                                                      f"target {mp} expects {exp} ({exp_share:.0%}): wrong marketplace export?"))

    # merge exact duplicates
    merged, exact_dups = {}, 0
    for r in rows:
        k = keyn(r["keyword"]) if r.get("keyword") else ""
        if not k:
            continue
        sv = num(r.get("search_volume"))
        cur = merged.get(k)
        if cur is None:
            merged[k] = dict(r, keyword=str(r["keyword"]).strip(), sv=sv, key=k, flags=[])
        else:
            exact_dups += 1
            if (sv or 0) > (cur["sv"] or 0):
                cur.update(dict(r, keyword=str(r["keyword"]).strip(), sv=sv, key=k))
    items = list(merged.values())

    # semantic clusters
    clusters = defaultdict(list)
    for it in items:
        sig = " ".join(sorted(set(meaningful(it["keyword"])))) or it["key"]
        clusters[sig].append(it)
    sem_dup_clusters = 0
    for sig, members in clusters.items():
        members.sort(key=lambda m: -(m["sv"] or 0))
        for m in members:
            m["cluster"] = sig
        if len(members) > 1:
            sem_dup_clusters += 1
            for m in members[1:]:
                m["flags"].append("SEMANTIC_DUPLICATE")

    terms = [t.strip() for t in a.product_terms.split(",") if t.strip()]
    term_tokens = [set(meaningful(t)) for t in terms]
    all_term_tokens = set().union(*term_tokens) if term_tokens else set()
    comps = [c.strip() for c in a.competitors.split(",") if c.strip()]
    excl = [c.strip() for c in a.exclude_terms.split(",") if c.strip()]
    verified = [x.strip().lower() for x in a.verified_claims.split(",") if x.strip()]

    def relevance(it):
        if not terms:
            return None
        kt = set(meaningful(it["keyword"]))
        best = 0.0
        for t, tt in zip(terms, term_tokens):
            if keyn(t) in it["key"]:
                return 1.0
            if tt:
                best = max(best, len(kt & tt) / len(tt) * 0.9)
        if kt & all_term_tokens:
            best = max(best, 0.4)
        return round(best, 2)

    eligible = []
    for it in items:
        it["relevance"] = relevance(it)
        reason = None
        if find_terms(it["keyword"], comps):
            reason, it["status"] = "competitor brand", "COMPETITOR_TERM"
        elif find_terms(it["keyword"], FORBIDDEN):
            reason, it["status"] = "prohibited / promotional / medical wording", "PROHIBITED_TERM"
        elif find_terms(it["keyword"], excl):
            reason, it["status"] = "excluded by user", "USER_EXCLUDED"
        else:
            cl = [c for c in find_terms(it["keyword"], STRICT_CLAIMS) if not any(v in c.lower() or c.lower() in v for v in verified)]
            if cl:
                reason, it["status"] = f"claim needs evidence ({', '.join(cl)})", "UNSUPPORTED_CLAIM"
        if reason is None and terms and (it["relevance"] or 0) < 0.4:
            reason, it["status"] = "not relevant to the product terms", "IRRELEVANT"
        if reason:
            it["tier"], it["reason"] = "EXCLUDE", reason
        elif "SEMANTIC_DUPLICATE" in it["flags"]:
            it["tier"], it["status"], it["reason"] = "EXCLUDE", "SEMANTIC_DUPLICATE", "variant of a stronger phrase (keep as backend synonym)"
        else:
            eligible.append(it)

    if not terms:
        for it in eligible:
            it["tier"], it["status"], it["reason"] = None, "NEEDS_PRODUCT_TERMS", "pass --product-terms from the verified TTX to judge relevance"
    else:
        vols = sorted([(it["sv"] or 0) for it in eligible])
        def pctl(v):
            if not vols:
                return 0
            return sum(1 for x in vols if x <= v) / len(vols)
        for it in eligible:
            it["score"] = round(it["relevance"] * pctl(it["sv"] or 0) * (1.0 if it["relevance"] >= 0.9 else 0.8), 4)
        ranked = sorted(eligible, key=lambda x: -x["score"])
        wc = lambda it: len(it["key"].split())  # noqa: E731
        # head terms (<= 3 words) compete for TIER_1/2; longer phrases are long-tail (TIER_3)
        t1 = [it for it in ranked if it["relevance"] >= 0.9 and wc(it) <= 3 and (it["sv"] or 0) > max(0, a.min_sv)][: a.top1]
        for it in t1:
            it["tier"] = "TIER_1_PRIMARY"
        t2 = [it for it in ranked if "tier" not in it and it["relevance"] >= 0.7 and wc(it) <= 3 and (it["sv"] or 0) > max(0, a.min_sv)][: a.top2]
        for it in t2:
            it["tier"] = "TIER_2_SECONDARY"
        for it in ranked:
            if "tier" in it:
                continue
            words = len(it["key"].split())
            if words >= 4 and it["relevance"] >= 0.7 and (it["sv"] or 0) > max(0, a.min_sv):
                it["tier"] = "TIER_3_LONG_TAIL"
            elif it["relevance"] >= 0.4:
                it["tier"] = "TIER_4_SEMANTIC"
            else:
                it["tier"] = "EXCLUDE"
                it["status"], it["reason"] = "IRRELEVANT", "relevance below 0.4"
        for it in ranked:
            it.setdefault("status", "USABLE")
            it.setdefault("reason", "")

    out_items = []
    for it in sorted(items, key=lambda x: (x.get("tier") is None, x.get("tier") == "EXCLUDE", -(x.get("score") or 0), -(x["sv"] or 0))):
        out_items.append(dict(keyword=it["keyword"], search_volume=it["sv"], relevance=it.get("relevance"), score=it.get("score"),
                              tier=it.get("tier"), status=it.get("status"), reason=it.get("reason"),
                              placement=TIER_PLACEMENT.get(it.get("tier"), ""), cluster=it.get("cluster"),
                              iq_score=num(it.get("iq_score")), competing_products=num(it.get("competing_products")),
                              title_density=num(it.get("title_density")), keyword_sales=num(it.get("keyword_sales")),
                              organic_rank=num(it.get("organic_rank")), cpc=num(it.get("cpc")), source_file=it["_src"]))
    tc = Counter(x["tier"] for x in out_items)
    st = Counter(x["status"] for x in out_items)
    report = {
        "total_keywords_in_files": len(rows), "after_exact_dedup": len(items), "exact_duplicates_removed": exact_dups,
        "semantic_duplicate_clusters": sem_dup_clusters,
        "usable_keywords": sum(tc[t] for t in ("TIER_1_PRIMARY", "TIER_2_SECONDARY", "TIER_3_LONG_TAIL", "TIER_4_SEMANTIC")),
        "irrelevant": st["IRRELEVANT"], "competitor_terms": st["COMPETITOR_TERM"], "prohibited_terms": st["PROHIBITED_TERM"],
        "unsupported_claims": st["UNSUPPORTED_CLAIM"], "user_excluded": st["USER_EXCLUDED"],
        "tier_1": tc["TIER_1_PRIMARY"], "tier_2": tc["TIER_2_SECONDARY"], "tier_3": tc["TIER_3_LONG_TAIL"], "tier_4": tc["TIER_4_SEMANTIC"],
        "excluded": tc["EXCLUDE"], "needs_product_terms": st["NEEDS_PRODUCT_TERMS"]}
    result = dict(marketplace=mp, seo_source_date=seo_date, seo_source_date_basis=date_basis, expected_language=exp,
                  language_shares=shares, flags=flags, sources=src, sanitization_report=report, keywords=out_items,
                  note="SEO data is search demand, never evidence of product facts. Marketplace-isolated: do not reuse for another marketplace.")
    if a.out:
        json.dump(result, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    if a.xlsx:
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "SEO"
        ws.append(["SKU", "Marketplace", "Keyword", "Search Volume", "Tier", "Placement", "Status", "Reason", "SEO Source Date"])
        for x in out_items:
            ws.append([a.sku, mp, x["keyword"], x["search_volume"], x["tier"], x["placement"], x["status"], x["reason"], seo_date])
        ws2 = wb.create_sheet("Sanitization")
        ws2.append(["Metric", "Value"])
        for k, v in report.items():
            ws2.append([k, v])
        for f in flags:
            ws2.append([f["code"], f["detail"]])
        wb.save(a.xlsx)
    print(f"SEO SANITIZATION REPORT [{mp}] source date {seo_date} ({date_basis})")
    for k, v in report.items():
        print(f"  {k:32} {v}")
    print("  language shares:", shares, "| expected:", exp)
    for f in flags:
        print(f"  FLAG {f['code']}: {f['detail']}")
    for x in out_items[:12]:
        if x["tier"] and x["tier"] != "EXCLUDE":
            print(f"  {x['tier']:17} sv={x['search_volume']}  {x['keyword']}  -> {x['placement']}")
    bad = bool(flags) or report["usable_keywords"] == 0 and not report["needs_product_terms"]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
