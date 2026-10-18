#!/usr/bin/env python3
"""Understand, normalize and open Amazon links from ANY marketplace (product by ASIN, category, search, store, seller).

Usage:
  amazon_link.py parse  URL [URL ...]                  offline: marketplace, country, language hint, kind, ASIN / browse node / keyword
  amazon_link.py build  --marketplace DE --asin B0XXXXXXXX [--kind product|reviews|offers] [--language de_DE]
  amazon_link.py build  --marketplace US --node 1234567            category page
  amazon_link.py build  --marketplace JP --keyword "pixel 8 ケース"  search page
  amazon_link.py all-markets --asin B0XXXXXXXX [--marketplaces DE,FR,IT]   the same ASIN on every marketplace
  amazon_link.py open   URL | --marketplace XX --asin A    open the canonical URL in YOUR default browser (prints it when no browser)
  amazon_link.py plan   URL | --marketplace XX --asin A    which Helium 10 MCP calls give the data behind this link
  amazon_link.py expand SHORTURL                       resolve amzn.to / a.co / amzn.eu redirects (headers only, no page content)

What this tool does NOT do: it never downloads or scrapes Amazon pages. Amazon's conditions of use restrict automated data
collection and the pages sit behind bot protection. Get product / category / keyword DATA from the Helium 10 MCP (see `plan`),
from the seller's own official APIs (SP-API for own listings), or from a page the user opens and shows. `open` only hands the
canonical URL to the user's own browser.

Safety: private / account pages (sign-in, cart, orders, account, wish lists) are refused and never processed; affiliate and
tracking parameters are stripped from the canonical URL; hosts must be exactly an Amazon marketplace domain (lookalikes such as
amazon.de.evil.com are rejected). The same ASIN can be absent or different on another marketplace: always verify per country.
Exit code 0 = ok, 1 = refused / not recognised, 2 = usage error.
"""
import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

try:
    from marketplaces import _DATA as MP_DATA
except ImportError:  # pragma: no cover
    sys.exit("marketplaces.py / marketplaces.json must be next to this script")

DOMAINS = {v["domain"]: k for k, v in MP_DATA["marketplaces"].items()}
EXTRA_DOMAINS = {"amazon.cn": None}  # known Amazon domains outside the table
SHORT_HOSTS = {"amzn.to", "a.co", "amzn.eu", "amzn.asia", "amzn.com", "amzn.in"}
ASIN_PATH = re.compile(r"/(?:dp|gp/product|gp/aw/d|product|exec/obidos/ASIN|gp/offer-listing|product-reviews|gp/customer-reviews|ask/questions/asin)/([A-Za-z0-9]{10})(?=[/?#]|$)")
LANG_PATH = re.compile(r"^/-/([a-z]{2}(?:_[A-Z]{2})?)(?=/)", re.I)
PRIVATE = re.compile(r"^/(ap/|gp/(?:css|cart|buy|your-account|yourstore|registry|wishlist|sign-?in|gift-?central|b2b/reports)|cart|hz/wishlist|your-account|orders|gp/aw/(?:c|ya)|gp/navigation/redirector)", re.I)
TRACKING = {"tag", "ref", "ref_", "linkcode", "linkid", "creative", "creativeasin", "camp", "qid", "sr", "crid", "sprefix", "dib", "dib_tag",
            "content-id", "pd_rd_w", "pd_rd_r", "pd_rd_wg", "pf_rd_p", "pf_rd_r", "pf_rd_s", "pf_rd_t", "pf_rd_i", "pf_rd_m", "psc", "th", "spla", "ie",
            "ascsubtag", "smid", "keywords_", "language", "utm_source", "utm_medium", "utm_campaign", "gclid", "fbclid"}

# Helium 10 MCP marketplace support, taken from the tool schemas (re-check if the MCP changes).
_A = "US CA MX DE ES IT FR UK IN NL AU JP AE BR SA".split()
MCP = {
    "get_listing_details": "US CA MX DE ES IT FR UK IN NL AE BR AU".split(),
    "retrieve_listing_by_asin": "US CA MX DE ES IT FR UK IN NL AU JP BE BR".split(),
    "get_keywords_by_asin": _A, "get_keywords_by_keyword": _A, "analyze_keywords": _A, "search_amazon_keywords": _A,
    "search_products": _A, "search_competitors_by_asin": _A, "search_amazon_brand_analytics": _A,
    "get_top_keywords": "US CA MX DE ES IT FR UK IN NL AE BR AU".split(),
    "search_browse_nodes": "US UK FR IT DE ES JP".split(),
    "check_asin_keyword_index": "US CA MX BR DE ES FR IT UK NL TR IN AE EG SA SE PL JP AU SG CN BE ZA IE".split(),
}


class Refused(Exception):
    pass


def marketplace_of(host):
    h = host.lower().rstrip(".")
    for prefix in ("www.", "smile.", "m.", "mobile."):
        if h.startswith(prefix):
            h = h[len(prefix):]
    if h in DOMAINS:
        return DOMAINS[h], h
    if h in EXTRA_DOMAINS:
        return EXTRA_DOMAINS[h], h
    return None, None


def parse(url):
    raw = url.strip()
    if not re.match(r"^https?://", raw, re.I):
        raw = "https://" + raw
    u = urllib.parse.urlparse(raw)
    host = (u.hostname or "").lower()
    if host in SHORT_HOSTS:
        return dict(url=url, kind="shortlink", host=host, note="short link: run `expand` (headers only) or ask the user for the full link")
    code, domain = marketplace_of(host)
    if domain is None:
        if re.search(r"(^|\.)amazon\.[a-z.]+$", host) and not host.endswith(tuple("." + d for d in DOMAINS)):
            raise Refused(f"'{host}' is not a known Amazon marketplace domain (lookalike or an unlisted country): add it to marketplaces.json only after checking")
        raise Refused(f"'{host}' is not an Amazon marketplace domain")
    path = u.path
    if PRIVATE.search(path):
        raise Refused("private / account / cart page: not processed (it can hold personal data); send the product or category link instead")
    q = {k.lower(): v for k, v in urllib.parse.parse_qs(u.query).items()}
    res = dict(url=url, host=host, domain=domain, marketplace=code, currency=MP_DATA["marketplaces"].get(code, {}).get("currency") if code else None,
               site_languages=MP_DATA["marketplaces"].get(code, {}).get("languages") if code else None)
    lm = LANG_PATH.match(path)
    lang = (lm.group(1) if lm else (q.get("language") or [None])[0])
    res["language_hint"] = lang.replace("-", "_") if lang else None
    if lang and code:
        short = lang.split("_")[0].lower()
        if short not in MP_DATA["marketplaces"][code]["languages"]:
            res["warning_language"] = f"language '{short}' is not in the table for {code}: VERIFY_IN_UI"
    stripped = sorted(k for k in q if k in TRACKING and k != "language")
    if "tag" in q:
        res["note_affiliate"] = "affiliate tag present and dropped from the canonical URL"
    res["tracking_params_removed"] = stripped
    asin = None
    m = ASIN_PATH.search(path)
    if m:
        asin = m.group(1).upper()
    elif "asin" in q and re.fullmatch(r"[A-Za-z0-9]{10}", q["asin"][0]):
        asin = q["asin"][0].upper()
    nodes = []
    for v in q.get("node", []) + q.get("bbn", []):
        nodes += re.findall(r"\d+", v)
    for v in q.get("rh", []):
        nodes += re.findall(r"n[:%3A]+(\d{3,})", urllib.parse.unquote(v))
    seg = re.findall(r"/(\d{3,})(?:/|$)", path)
    if re.search(r"/(?:zgbs|bestsellers|new-releases|movers-and-shakers|most-wished-for|most-gifted)", path) and seg:
        nodes += seg[-1:]
    if re.search(r"/b/?(?:/|$)", path) and not nodes:
        nodes += re.findall(r"/b/(\d{3,})", path)
    nodes = list(dict.fromkeys(nodes))
    kw = (q.get("k") or q.get("field-keywords") or q.get("keywords") or [None])[0]
    if asin:
        sub = "reviews" if re.search(r"product-reviews|customer-reviews", path) else "offers" if "offer-listing" in path else "qa" if "/ask/" in path else "product"
        res.update(kind="product", subkind=sub, asin=asin)
        res["canonical_url"] = canonical(code, domain, "product", asin=asin, sub=sub if sub in ("reviews", "offers") else "product")
    elif re.search(r"/(?:zgbs|bestsellers|new-releases|movers-and-shakers|most-wished-for|most-gifted)", path):
        board = re.search(r"/(zgbs|bestsellers|new-releases|movers-and-shakers|most-wished-for|most-gifted)", path).group(1)
        res.update(kind="ranking", board=board.replace("zgbs", "bestsellers"), browse_nodes=nodes, category_path_slugs=[s for s in path.split("/") if s and not s.isdigit() and s not in ("gp", "zgbs", "bestsellers", "new-releases", "movers-and-shakers", "most-wished-for", "most-gifted") and not s.startswith("ref=")])
        res["canonical_url"] = None
    elif "/stores/" in path or path.startswith("/stores"):
        res.update(kind="store", store_path=path)
        res["canonical_url"] = f"https://www.{domain}{path}"
    elif re.search(r"^/(?:sp|gp/aag/main|gp/seller)", path) and q.get("seller"):
        res.update(kind="seller", seller_id=q["seller"][0])
        res["canonical_url"] = f"https://www.{domain}/sp?seller={q['seller'][0]}"
    elif path.startswith("/s") and (kw or nodes):
        res.update(kind="search", keyword=kw, browse_nodes=nodes)
        res["canonical_url"] = canonical(code, domain, "search", keyword=kw, node=nodes[0] if nodes else None)
    elif nodes or re.search(r"/b/|/gp/browse", path):
        res.update(kind="category", browse_nodes=nodes, category_path_slugs=[s for s in path.split("/") if s and not s.isdigit() and s not in ("b", "gp", "browse.html") and not s.startswith("ref=")][:6])
        res["canonical_url"] = canonical(code, domain, "category", node=nodes[0]) if nodes else None
        if not nodes:
            res["warning"] = "category link without a browse node id: ask the user to open the category and copy a link containing node=..."
    elif path in ("", "/"):
        res.update(kind="home", canonical_url=f"https://www.{domain}/")
    else:
        raise Refused("link type not recognised (supported: product/ASIN, category, ranking lists, search, store, seller)")
    return res


def canonical(code, domain, kind, asin=None, node=None, keyword=None, sub="product", language=None):
    base = f"https://www.{domain}"
    if kind == "product":
        path = {"product": "/dp/", "reviews": "/product-reviews/", "offers": "/gp/offer-listing/"}[sub] + asin
        url = base + path
    elif kind == "category":
        url = f"{base}/b?node={node}"
    elif kind == "search":
        url = f"{base}/s?" + urllib.parse.urlencode({k: v for k, v in (("k", keyword), ("rh", f"n:{node}" if node else None)) if v})
    else:
        raise Refused(f"cannot build kind {kind}")
    if language:
        url += ("&" if "?" in url else "?") + "language=" + language
    return url


def need_market(code):
    code = (code or "").upper()
    code = MP_DATA.get("aliases", {}).get(code, code)
    if code not in MP_DATA["marketplaces"]:
        raise Refused(f"unknown marketplace '{code}' (see marketplaces.py --list)")
    return code, MP_DATA["marketplaces"][code]["domain"]


def mcp_line(tool, code, args, why):
    ok = code in MCP.get(tool, [code])
    return dict(tool=f"mcp__Helium_10__{tool}", arguments=args, marketplace_supported=ok, purpose=why,
                note=None if ok else f"{tool} does not list {code}: report SEO/DATA_SOURCE_UNAVAILABLE_FOR_MARKETPLACE and ask for an export file")


def plan(info):
    code, kind = info.get("marketplace"), info.get("kind")
    steps = []
    if kind == "product":
        a = info["asin"]
        steps = [
            mcp_line("get_listing_details", code, {"main_asin": a, "marketplace": code}, "full listing profile: title, LQS, BSR, price, sales/revenue estimates, variations, top-10 keywords"),
            mcp_line("retrieve_listing_by_asin", code, {"asin": a, "marketplace": code}, "live catalog title/bullets/description and images (the listing's current copy)"),
            mcp_line("get_keywords_by_asin", code, {"asin": a, "marketplace": code, "limit": 150}, "Cerebro: keywords this ASIN is visible for (competitor reverse search)"),
            mcp_line("search_competitors_by_asin", code, {"asin": a, "marketplace": code}, "similar competing listings with price/sales/reviews"),
            dict(tool="competitor_pack.py ingest", arguments={"asin": a, "marketplace": code}, purpose="if this is a COMPETITOR's product: save the two results above as JSON and build the reference card (images + copy, REFERENCE_ONLY, copy guard) - see references/13-competitor-reference.md of the Product Intelligence agent"),
            dict(tool="mcp__Helium_10__get_asin_price_history / get_asin_bsr_history / get_asin_reviews_history", arguments={"asin": a},
                 purpose="history of price, BSR and reviews (check the tool schema for marketplace support)"),
        ]
        steps.append(dict(tool="own listings only", purpose="the seller's own ASINs: SP-API Catalog Items / Listings Items with the seller's credentials"))
    elif kind in ("category", "ranking"):
        nodes = info.get("browse_nodes") or []
        steps = [mcp_line("search_products", code, {"marketplace": code, "filters": {"category": nodes or ["<category name>"]}, "sort_by": "sales_rank", "limit": 25}, "top active products of this category (the category filter accepts browse node ids)"),
                 mcp_line("search_amazon_keywords", code, {"marketplace": code, "filters": {"category": nodes or ["<category name>"]}}, "keyword landscape of the category"),
                 dict(tool="mcp__Helium_10__search_browse_nodes", arguments={"marketplace": code, "query": "<category name>"}, marketplace_supported=code in MCP["search_browse_nodes"],
                      purpose="name -> candidate browse node ids (the reverse, node id -> name, is not offered: take the name from the link slugs or the user)")]
        if info.get("category_path_slugs"):
            steps[0]["category_name_hint"] = " / ".join(info["category_path_slugs"])
    elif kind == "search":
        steps = [mcp_line("get_keywords_by_keyword", code, {"seed_keyword": info.get("keyword"), "marketplace": code}, "Magnet: related keywords and volumes"),
                 mcp_line("analyze_keywords", code, {"keywords": [info.get("keyword")], "marketplace": code}, "volume / CPC / competition of this exact phrase"),
                 mcp_line("search_products", code, {"marketplace": code, "filters": {"title_include_keyword": info.get("keyword")}, "sort_by": "-monthly_revenue"}, "active products whose title contains the phrase")]
    elif kind == "seller":
        steps = [dict(tool="mcp__Helium_10__search_products", arguments={"marketplace": code, "filters": {"seller_include": "<seller NAME>"}},
                      purpose="products of a seller (needs the seller name; a seller id alone is not searchable here). Seller id: " + str(info.get("seller_id")))]
    else:
        steps = [dict(purpose="no data plan for this link type; ask the user which product, category or keyword to analyse")]
    return dict(link=info.get("canonical_url") or info.get("url"), marketplace=code, kind=kind,
                data_sources=steps,
                rules=["Session handling for the MCP: first call without session_id, then echo the session_id returned in `[gateway-meta]`.",
                       "No page scraping; the user may open the link (`amazon_link.py open`) and paste what they see.",
                       "Use the marketplace of the link for every call; never reuse another country's data.",
                       "Record source (tool, marketplace, ASIN/node/keyword, date) in the project memory."])


def expand(short):
    u = urllib.parse.urlparse(short if short.startswith("http") else "https://" + short)
    if (u.hostname or "").lower() not in SHORT_HOSTS:
        raise Refused("only Amazon short-link hosts can be expanded")
    url = u.geturl()
    for _ in range(5):
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "amazon-agents-link-expander/1.0"})

        class NoRedir(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *a, **k):
                return None
        try:
            urllib.request.build_opener(NoRedir).open(req, timeout=20)
            break
        except urllib.error.HTTPError as e:
            loc = e.headers.get("Location")
            if e.code in (301, 302, 303, 307, 308) and loc:
                url = urllib.parse.urljoin(url, loc)
                if (urllib.parse.urlparse(url).hostname or "").lower() not in SHORT_HOSTS:
                    break
                continue
            raise Refused(f"HTTP {e.code} while expanding")
        except urllib.error.URLError as e:
            raise Refused(f"network error: {e.reason}")
    return url


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("parse"); p.add_argument("urls", nargs="+")
    b = sub.add_parser("build")
    for s in (b,):
        s.add_argument("--marketplace", required=True); s.add_argument("--asin"); s.add_argument("--node"); s.add_argument("--keyword")
        s.add_argument("--kind", choices=["product", "reviews", "offers"], default="product"); s.add_argument("--language")
    am = sub.add_parser("all-markets"); am.add_argument("--asin", required=True); am.add_argument("--marketplaces"); am.add_argument("--kind", choices=["product", "reviews"], default="product")
    o = sub.add_parser("open"); o.add_argument("url", nargs="?"); o.add_argument("--marketplace"); o.add_argument("--asin"); o.add_argument("--print-only", action="store_true")
    pl = sub.add_parser("plan"); pl.add_argument("url", nargs="?"); pl.add_argument("--marketplace"); pl.add_argument("--asin")
    ex = sub.add_parser("expand"); ex.add_argument("url")
    a = ap.parse_args()
    try:
        if a.cmd == "parse":
            out = [parse(u) for u in a.urls]
            print(json.dumps(out if len(out) > 1 else out[0], ensure_ascii=False, indent=2))
        elif a.cmd == "build":
            code, domain = need_market(a.marketplace)
            if a.asin:
                if not re.fullmatch(r"[A-Za-z0-9]{10}", a.asin):
                    raise Refused("ASIN must be 10 letters/digits")
                print(canonical(code, domain, "product", asin=a.asin.upper(), sub=a.kind, language=a.language))
            elif a.node:
                print(canonical(code, domain, "category", node=a.node, language=a.language))
            elif a.keyword:
                print(canonical(code, domain, "search", keyword=a.keyword, language=a.language))
            else:
                raise Refused("give --asin, --node or --keyword")
        elif a.cmd == "all-markets":
            if not re.fullmatch(r"[A-Za-z0-9]{10}", a.asin):
                raise Refused("ASIN must be 10 letters/digits")
            codes = [need_market(c)[0] for c in a.marketplaces.split(",")] if a.marketplaces else list(MP_DATA["marketplaces"])
            for c in codes:
                print(f"{c}\t{canonical(c, MP_DATA['marketplaces'][c]['domain'], 'product', asin=a.asin.upper(), sub=a.kind)}")
            print("NOTE: the same ASIN may not exist, or may be a different product, on another marketplace: check each page/data source.", file=sys.stderr)
        elif a.cmd in ("open", "plan"):
            if a.url:
                info = parse(a.url)
                if info["kind"] == "shortlink":
                    raise Refused(info["note"])
            elif a.marketplace and a.asin:
                code, domain = need_market(a.marketplace)
                info = dict(parse(canonical(code, domain, "product", asin=a.asin.upper())))
            else:
                raise Refused("give a URL or --marketplace and --asin")
            if a.cmd == "plan":
                print(json.dumps(plan(info), ensure_ascii=False, indent=2))
            else:
                target = info.get("canonical_url") or info["url"]
                print(target)
                if not a.print_only:
                    import webbrowser
                    ok = webbrowser.open(target)
                    print("opened in the default browser" if ok else "no browser available here: open the URL above yourself", file=sys.stderr)
        elif a.cmd == "expand":
            print(expand(a.url))
    except Refused as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
