#!/usr/bin/env python3
"""Competitor REFERENCE pack: look at a competitor listing's images and copy to prepare a similar product - without copying it.

Data comes from the Helium 10 MCP (never from scraping Amazon pages):
  1. amazon_link.py plan URL                         -> which calls to make for the link
  2. MCP retrieve_listing_by_asin(asin, marketplace)  -> images [{url, variant}], product_name, item_highlight, bullet_points, description
     MCP get_listing_details(main_asin, marketplace)  -> price, BSR, reviews, LQS, sales estimates, top keywords (optional)
     Save each tool result as JSON (the agent writes the file), then:

Usage:
  competitor_pack.py ingest LISTING.json [DETAILS.json] --marketplace DE --asin B0XXXXXXXX --out DIR
                     [--download-images] [--max-images 12] [--source-url URL]
  competitor_pack.py matrix  CARD.json [CARD.json ...]        compare competitors: price, BSR, reviews, images, bullets, feature mentions
  competitor_pack.py similarity CARD.json OURS.json [--ngram 6] [--max-shared 1]
        copy guard: OURS.json = our content (title, bullet_points, description, ...) -> exit 1 if it shares word sequences with the competitor
  competitor_pack.py brands CARD.json [...]                   brand guesses -> --competitors list for seo_import.py / content_check.py

Rules built into the tool
  * REFERENCE ONLY: the card is stamped use=REFERENCE_ONLY. Competitor text, images, brand names, claims and certifications are never
    copied into our listing, and competitor facts are not evidence for our product (spec: competitor data is the lowest source).
  * Images are downloaded only from Amazon image hosts, only the URLs the MCP returned, https only, sequentially (1 s apart), capped
    in number and size. No HTML page is ever fetched.
  * Look at the downloaded files with your image viewer; the card lists local paths, sizes, sha256 and main-image checks.
  * A "similar product" still needs its OWN verified TTX, images and claims; check designs, trademarks and patents of the competitor
    before launch (IP_REVIEW_REQUIRED) - this tool cannot judge infringement.
Exit code 0 = ok, 1 = copy guard / ingest problem, 2 = usage error.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from content_check import STRICT_CLAIMS, STOP, find_terms, tokens

IMG_HOSTS = ("m.media-amazon.com", "images-na.ssl-images-amazon.com", "images-eu.ssl-images-amazon.com", "images-fe.ssl-images-amazon.com",
             "ssl-images-amazon.com", "images-amazon.com")
TEST_HOST = os.environ.get("COMPETITOR_PACK_TEST_ALLOW_HOST")  # test hook only
UNIT_RE = re.compile(r"(?<![\w-])(\d+(?:[.,]\d+)?)\s?(mm|cm|m|in|inch|zoll|ft|g|kg|oz|lb|ml|l|cl|fl\.? ?oz|v|w|kw|mah|wh|hz|ghz|gb|tb|mp|pcs|pack|stück)(?![\w-])", re.I)
CERT_RE = re.compile(r"\b(IP\d{2}|CE|FCC|RoHS|REACH|FDA|BPA[- ]?free|MIL-?STD[- ]?\d+\w*|TÜV|GS|UL\s?\d*|ISO\s?\d+)\b", re.I)


def find_key(obj, names, depth=0):
    """First value in a nested JSON whose key (lowercased, _ and spaces ignored) is in names."""
    if depth > 6:
        return None
    if isinstance(obj, dict):
        for k, v in obj.items():
            if re.sub(r"[\s_-]+", "", str(k).lower()) in names and v not in (None, "", [], {}):
                return v
        for v in obj.values():
            r = find_key(v, names, depth + 1)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj[:5]:
            r = find_key(v, names, depth + 1)
            if r is not None:
                return r
    return None


def as_text(v):
    if v is None:
        return ""
    if isinstance(v, list):
        return "\n".join(str(x) for x in v)
    return str(v)


def img_ok(url):
    u = urllib.parse.urlparse(url)
    h = (u.hostname or "").lower()
    if TEST_HOST and h == TEST_HOST:
        return True
    return u.scheme == "https" and (h in IMG_HOSTS or h.endswith(".media-amazon.com") or h.endswith(".ssl-images-amazon.com"))


def download(url, path_base, max_bytes):
    req = urllib.request.Request(url, headers={"User-Agent": "amazon-agents-reference-viewer/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        ctype = r.headers.get("Content-Type", "")
        if not ctype.lower().startswith("image/"):
            raise ValueError(f"not an image ({ctype})")
        data = r.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError("image larger than the size cap")
    ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}.get(ctype.split(";")[0].lower(), ".img")
    path = path_base + ext
    with open(path, "wb") as f:
        f.write(data)
    return path, data


def image_facts(path, data):
    facts = dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    try:
        from PIL import Image
        im = Image.open(path)
        facts.update(width=im.size[0], height=im.size[1], mode=im.mode)
        rgb = im.convert("RGB")
        w, h = rgb.size
        corners = [rgb.getpixel(p) for p in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1))]
        facts["white_background_corners"] = all(min(c) >= 250 for c in corners)
    except Exception:  # noqa: BLE001
        facts["note"] = "Pillow not available or unreadable image: dimensions not checked"
    return facts


def ingest(a):
    listing = json.load(open(a.listing, encoding="utf-8"))
    details = json.load(open(a.details, encoding="utf-8")) if a.details else {}
    asin = a.asin.upper()
    if not re.fullmatch(r"[A-Z0-9]{10}", asin):
        sys.exit("ASIN must be 10 letters/digits")
    title = as_text(find_key(listing, {"productname", "title"})) or as_text(find_key(details, {"title", "productname"}))
    bullets = find_key(listing, {"bulletpoints", "bullets"}) or []
    if isinstance(bullets, str):
        bullets = [b.strip() for b in bullets.split("\n") if b.strip()]
    highlight = as_text(find_key(listing, {"itemhighlight", "itemhighlights"}))
    desc = as_text(find_key(listing, {"description", "productdescription"}))
    imgs = find_key(listing, {"images"}) or []
    images = []
    for i, im in enumerate(imgs if isinstance(imgs, list) else []):
        url = im.get("url") if isinstance(im, dict) else str(im)
        if url:
            images.append(dict(index=i + 1, variant=(im.get("variant") if isinstance(im, dict) else None), url=url, host_allowed=img_ok(url)))
    metrics = {}
    for name, keys in (("price", {"price"}), ("bsr", {"bsr", "bestsellersrank", "categorybsr", "salesrank"}), ("reviews", {"reviewcount", "reviews", "numberofreviews"}),
                       ("rating", {"rating", "reviewsrating", "reviewrating"}), ("listing_quality_score", {"lqs", "listingqualityscore"}),
                       ("image_count", {"imagecount", "numberofimages"}), ("variation_count", {"variationcount", "variationscount"}),
                       ("monthly_sales", {"monthlysales", "parentsales", "sales", "estimatedsales"}), ("monthly_revenue", {"monthlyrevenue", "parentrevenue", "revenue"}),
                       ("seller", {"sellername", "seller", "brand"}), ("top_keywords", {"topkeywords", "keywords"})):
        v = find_key(details, keys)
        if v is not None:
            metrics[name] = v
    text_all = "\n".join([title, highlight, *bullets, desc])
    feats = sorted({f"{m.group(1)} {m.group(2).lower()}" for m in UNIT_RE.finditer(text_all)})
    certs = sorted({m.group(1).upper() for m in CERT_RE.finditer(text_all)})
    claims = sorted({c for c in find_terms(text_all, STRICT_CLAIMS)})
    brand_guess = (title.split() or [""])[0].strip(",.:-") if title else ""
    card = dict(use="REFERENCE_ONLY", metrics_note="metrics are copied as returned by the tool; money amounts may be in minor units (cents) - check the tool output", asin=asin, marketplace=a.marketplace.upper(), source_url=a.source_url,
                retrieved_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                sources=dict(listing_file=os.path.basename(a.listing), details_file=os.path.basename(a.details) if a.details else None,
                             tools=["retrieve_listing_by_asin"] + (["get_listing_details"] if a.details else [])),
                copy=dict(title=title, item_highlight=highlight, bullet_points=bullets, description=desc,
                          title_chars=len(title), bullet_count=len(bullets), description_chars=len(desc)),
                images=images, metrics=metrics,
                observations=dict(brand_guess=brand_guess, measurable_features=feats, certification_mentions=certs,
                                  claims_needing_evidence=claims,
                                  note="Observations are about the COMPETITOR. Not evidence for our product; not to be copied."),
                warnings=[], flags=["IP_REVIEW_REQUIRED", "COMPETITOR_BRAND_EXCLUDE"])
    if not (title or bullets or desc):
        card["warnings"].append("no listing text found in the file: check that it is the saved result of retrieve_listing_by_asin")
    if not images:
        card["warnings"].append("no images in the listing result")
    if a.download_images:
        out = os.path.join(a.out, "images")
        os.makedirs(out, exist_ok=True)
        done = 0
        for im in images:
            if done >= a.max_images:
                im["skipped"] = "max-images cap"
                continue
            if not im["host_allowed"]:
                im["skipped"] = "host not an Amazon image host"
                continue
            try:
                if done:
                    time.sleep(a.delay)
                base = os.path.join(out, f"{asin}_{im['index']:02d}_{re.sub(r'[^A-Za-z0-9]+', '', str(im.get('variant') or 'img'))[:12]}")
                path, data = download(im["url"], base, a.max_mb * (1 << 20))
                im.update(path=path, **image_facts(path, data))
                done += 1
            except (urllib.error.URLError, ValueError, OSError) as e:
                im["error"] = str(e)
        card["images_downloaded"] = done
        if images and images[0].get("path") and images[0].get("white_background_corners") is False:
            card["warnings"].append("first image does not have a white background (MAIN image rules apply to OUR image, not to the competitor)")
    os.makedirs(a.out, exist_ok=True)
    path = os.path.join(a.out, f"competitor_{asin}_{a.marketplace.upper()}.json")
    json.dump(card, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"wrote {path}: title {len(title)} chars, {len(bullets)} bullets, description {len(desc)} chars, {len(images)} images"
          + (f", {card.get('images_downloaded', 0)} downloaded to {os.path.join(a.out, 'images')}" if a.download_images else ""))
    for w in card["warnings"]:
        print("WARNING:", w)
    print("USE: REFERENCE_ONLY - analyse structure, features and gaps; do not copy text, images, brand, claims or certifications.")
    return 0


def matrix(a):
    cards = [json.load(open(p, encoding="utf-8")) for p in a.cards]
    print(f"{'ASIN':11} {'MP':3} {'price':>8} {'BSR':>8} {'reviews':>8} {'rating':>6} {'imgs':>4} {'bullets':>7} {'title':>5}  brand?")
    feats = {}
    for c in cards:
        m = c.get("metrics", {})
        print(f"{c['asin']:11} {c['marketplace']:3} {str(m.get('price', '-')):>8} {str(m.get('bsr', '-'))[:8]:>8} {str(m.get('reviews', '-')):>8} "
              f"{str(m.get('rating', '-')):>6} {len(c.get('images', [])):>4} {c['copy']['bullet_count']:>7} {c['copy']['title_chars']:>5}  {c['observations']['brand_guess']}")
        for f in c["observations"]["measurable_features"] + c["observations"]["certification_mentions"]:
            feats.setdefault(f, set()).add(c["asin"])
    if feats:
        print("\nfeature / spec mentions across competitors (what shoppers are told; verify against OUR product before using any):")
        for f, who in sorted(feats.items(), key=lambda kv: -len(kv[1]))[:30]:
            print(f"  {len(who)}/{len(cards)}  {f}")
    return 0


def ngrams(words, n):
    return {" ".join(words[i:i + n]) for i in range(len(words) - n + 1)}


def similarity(a):
    card = json.load(open(a.card, encoding="utf-8"))
    ours = json.load(open(a.ours, encoding="utf-8"))
    ours = ours.get("content", ours)
    comp_text = "\n".join([card["copy"]["title"], card["copy"]["item_highlight"], *card["copy"]["bullet_points"], card["copy"]["description"]])
    our_text = "\n".join([as_text(ours.get(k)) for k in ("title", "item_highlights", "item_highlight", "bullet_points", "description")])
    cw = [w for w in tokens(comp_text)]
    ow = [w for w in tokens(our_text)]
    shared = sorted(ngrams(cw, a.ngram) & ngrams(ow, a.ngram))
    shared = [s for s in shared if sum(1 for w in s.split() if w not in STOP) >= max(2, a.ngram // 2)]
    jac = (len(ngrams(cw, 3) & ngrams(ow, 3)) / max(1, len(ngrams(cw, 3) | ngrams(ow, 3))))
    print(f"competitor {card['asin']} vs our text: {len(shared)} shared {a.ngram}-word sequence(s); 3-gram overlap {jac:.0%}")
    for s in shared[:10]:
        print(f"  SHARED: '{s}'")
    bad = len(shared) > a.max_shared
    print("COPY GUARD:", "FAIL - rewrite these passages in our own words from OUR verified facts" if bad else "PASS")
    return 1 if bad else 0


def brands(a):
    out = []
    for p in a.cards:
        c = json.load(open(p, encoding="utf-8"))
        b = c["observations"]["brand_guess"]
        if b:
            out.append(b)
    print(",".join(dict.fromkeys(out)))
    print("(first word of the competitor title: a GUESS - confirm, then pass as --competitors to seo_import.py / content_check.py)", file=sys.stderr)
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("ingest")
    i.add_argument("listing")
    i.add_argument("details", nargs="?")
    i.add_argument("--marketplace", required=True)
    i.add_argument("--asin", required=True)
    i.add_argument("--out", required=True)
    i.add_argument("--source-url")
    i.add_argument("--download-images", action="store_true")
    i.add_argument("--max-images", type=int, default=12)
    i.add_argument("--max-mb", type=int, default=10)
    i.add_argument("--delay", type=float, default=1.0)
    m = sub.add_parser("matrix")
    m.add_argument("cards", nargs="+")
    s = sub.add_parser("similarity")
    s.add_argument("card")
    s.add_argument("ours")
    s.add_argument("--ngram", type=int, default=6)
    s.add_argument("--max-shared", type=int, default=1)
    b = sub.add_parser("brands")
    b.add_argument("cards", nargs="+")
    a = ap.parse_args()
    return {"ingest": ingest, "matrix": matrix, "similarity": similarity, "brands": brands}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
