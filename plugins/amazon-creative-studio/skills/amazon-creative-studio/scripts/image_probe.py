#!/usr/bin/env python3
"""Measure an image so the agent can READ it reliably (facts first, then visual judgment).

Usage:
  image_probe.py IMG [IMG ...] [--tiles DIR] [--json]
  image_probe.py --sheet OUT.jpg IMG [IMG ...]        contact sheet of up to 12 images for side-by-side viewing

Per image: format, pixel size, aspect ratio, DPI, file size, alpha, EXIF orientation, background kind and whiteness,
content bounding box and fill percent, 3x3 zone occupancy, dominant palette (hex + share), brightness/contrast,
sharpness estimate, edge-density hint for text areas, plus warnings. `--tiles DIR` also writes a downscaled preview and
2x2 zoomed crops (preview.jpg, tile_TL/TR/BL/BR.jpg) that you then open and LOOK at to read labels, small print and fine details.

This tool measures; it does not understand the picture. The agent must then view the image itself (vision) and fill the
visual reading template in references/image-reading.md. Never treat the numbers as proof of fidelity, legibility or claims.
Exit code 0 = ok, 2 = usage / unreadable file.
"""
import argparse
import json
import os
import sys

try:
    from PIL import Image, ImageChops, ImageFilter, ImageOps, ImageStat
except ImportError:
    sys.exit("Pillow is required: pip install Pillow")

Image.MAX_IMAGE_PIXELS = 300_000_000


def hexc(rgb):
    return "#%02X%02X%02X" % tuple(rgb)


def bg_kind(im):
    w, h = im.size
    pts = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2)]
    px = [im.getpixel(p) for p in pts]
    avg = tuple(sum(c[i] for c in px) // len(px) for i in range(3))
    spread = max(max(c[i] for c in px) - min(c[i] for c in px) for i in range(3))
    if spread <= 6 and min(avg) >= 250:
        kind = "pure_white"
    elif spread <= 10 and min(avg) >= 235:
        kind = "near_white"
    elif spread <= 12:
        kind = "solid_color"
    else:
        kind = "varied_or_scene"
    return kind, hexc(avg), spread


def content_bbox(im, ref):
    """Bounding box of pixels that differ from the reference background by more than a small tolerance."""
    small = im.copy()
    small.thumbnail((600, 600))
    bg = Image.new("RGB", small.size, ref)
    diff = ImageOps.grayscale(ImageChops.difference(small, bg))
    mask = diff.point(lambda v: 255 if v > 18 else 0)
    box = mask.getbbox()
    return small.size, box, mask


def zones(mask):
    w, h = mask.size
    out = []
    for r in range(3):
        row = []
        for c in range(3):
            tile = mask.crop((c * w // 3, r * h // 3, (c + 1) * w // 3, (r + 1) * h // 3))
            hist = tile.histogram()
            tot = sum(hist) or 1
            row.append(round(100 * hist[255] / tot))
        out.append(row)
    return out


def palette(im, n=6):
    small = im.copy()
    small.thumbnail((200, 200))
    q = small.quantize(colors=n, method=Image.MEDIANCUT)
    pal = q.getpalette()
    counts = sorted(q.getcolors(), reverse=True)
    tot = sum(c for c, _ in counts)
    return [{"hex": hexc(pal[i * 3:i * 3 + 3]), "share_pct": round(100 * c / tot)} for c, i in counts]


def text_hint(gray):
    """Share of 32px blocks with high local edge density: a hint that text/graphics exist, not OCR."""
    edges = gray.filter(ImageFilter.FIND_EDGES)
    edges.thumbnail((640, 640))
    w, h = edges.size
    b = 24
    hot = tot = 0
    for y in range(0, h - b, b):
        for x in range(0, w - b, b):
            tot += 1
            if ImageStat.Stat(edges.crop((x, y, x + b, y + b))).mean[0] > 28:
                hot += 1
    return round(100 * hot / max(tot, 1))


def probe(path, tiles=None):
    res = {"file": path, "bytes": os.path.getsize(path)}
    with Image.open(path) as raw:
        res["format"] = raw.format
        res["mode"] = raw.mode
        res["dpi"] = raw.info.get("dpi")
        try:
            orient = (raw.getexif() or {}).get(274)
        except Exception:
            orient = None
        res["exif_orientation"] = orient
        im = ImageOps.exif_transpose(raw)
        res["has_alpha"] = im.mode in ("RGBA", "LA") or "transparency" in im.info
        if res["has_alpha"]:
            bgw = Image.new("RGBA", im.size, (255, 255, 255, 255))
            im = Image.alpha_composite(bgw, im.convert("RGBA"))
        im = im.convert("RGB")
    w, h = im.size
    res["pixels"] = f"{w}x{h}"
    res["aspect"] = round(w / h, 3)
    kind, avg, spread = bg_kind(im)
    res["background"] = {"kind": kind, "avg": avg, "corner_spread": spread}
    ref = tuple(int(avg[i:i + 2], 16) for i in (1, 3, 5))
    (sw, sh), box, mask = content_bbox(im, ref)
    if box:
        bw, bh = box[2] - box[0], box[3] - box[1]
        res["content_bbox_pct"] = {"left": round(100 * box[0] / sw), "top": round(100 * box[1] / sh),
                                   "right": round(100 * box[2] / sw), "bottom": round(100 * box[3] / sh)}
        res["fill_pct"] = {"width": round(100 * bw / sw), "height": round(100 * bh / sh)}
        res["touches_edge"] = box[0] <= 1 or box[1] <= 1 or box[2] >= sw - 1 or box[3] >= sh - 1
        res["zones_3x3_pct"] = zones(mask)
    else:
        res["content_bbox_pct"] = None
    gray = ImageOps.grayscale(im)
    st = ImageStat.Stat(gray)
    res["brightness_mean"] = round(st.mean[0])
    res["contrast_stddev"] = round(st.stddev[0])
    sm = gray.copy()
    sm.thumbnail((800, 800))
    res["sharpness"] = round(ImageStat.Stat(sm.filter(ImageFilter.FIND_EDGES)).var[0])
    res["palette"] = palette(im)
    res["edge_dense_blocks_pct"] = text_hint(gray)
    warn = []
    if min(w, h) < 1000:
        warn.append("LOW_RESOLUTION: shorter side < 1000 px (zoom/mobile risk)")
    if res["sharpness"] < 150:
        warn.append("POSSIBLY_BLURRY: low edge variance (check visually)")
    if res.get("touches_edge") and kind in ("pure_white", "near_white"):
        warn.append("CONTENT_TOUCHES_EDGE: product may be clipped")
    if res["has_alpha"]:
        warn.append("HAS_ALPHA: composited on white for measurement")
    if orient and orient != 1:
        warn.append(f"EXIF_ORIENTATION={orient}: applied before measuring")
    res["warnings"] = warn
    if tiles:
        os.makedirs(tiles, exist_ok=True)
        base = os.path.splitext(os.path.basename(path))[0]
        pv = im.copy()
        pv.thumbnail((1600, 1600))
        pv.save(os.path.join(tiles, f"{base}_preview.jpg"), quality=88)
        for name, (cx, cy) in {"TL": (0, 0), "TR": (1, 0), "BL": (0, 1), "BR": (1, 1)}.items():
            t = im.crop((cx * w // 2, cy * h // 2, (cx + 1) * w // 2, (cy + 1) * h // 2))
            t.thumbnail((1600, 1600))
            t.save(os.path.join(tiles, f"{base}_tile_{name}.jpg"), quality=90)
        res["tiles_dir"] = tiles
    return res


def sheet(out, paths):
    imgs = []
    for p in paths[:12]:
        with Image.open(p) as r:
            i = ImageOps.exif_transpose(r).convert("RGB")
            i.thumbnail((400, 400))
            imgs.append(i)
    cols = min(4, len(imgs))
    rows = (len(imgs) + cols - 1) // cols
    canvas = Image.new("RGB", (cols * 410 + 10, rows * 410 + 10), (240, 240, 240))
    for n, i in enumerate(imgs):
        canvas.paste(i, (10 + (n % cols) * 410, 10 + (n // cols) * 410))
    canvas.save(out, quality=88)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("images", nargs="+")
    ap.add_argument("--tiles")
    ap.add_argument("--sheet")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    try:
        if a.sheet:
            print(sheet(a.sheet, a.images))
            return 0
        results = [probe(p, a.tiles) for p in a.images]
    except (OSError, ValueError) as e:
        print(f"cannot read image: {e}", file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for r in results:
            print(f"{r['file']}: {r['pixels']} {r['format']} bg={r['background']['kind']} {r['background']['avg']} "
                  f"fill={r.get('fill_pct')} edge_dense={r['edge_dense_blocks_pct']}% palette="
                  + ",".join(p['hex'] for p in r['palette'][:4]))
            for w in r["warnings"]:
                print("  WARN", w)
        print(json.dumps(results, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
