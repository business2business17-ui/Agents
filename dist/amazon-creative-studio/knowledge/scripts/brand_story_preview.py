#!/usr/bin/env python3
"""Brand Story preview mockups: cards (362x453 / logo 315x145) laid over the background.

Writes separate Desktop (1464x625) and Mobile (463x625) previews for the first screen,
a scrolled state and the extreme (last) card position, with the working safe margins
drawn as a dashed frame. Illustrative geometry, not the exact Amazon UI.

  python3 brand_story_preview.py --bg-desktop bg_d.jpg --bg-mobile bg_m.jpg \
      --cards c1.png c2.png c3.png --out previews/
"""
import argparse
import os
import sys

DESKTOP = (1464, 625)
MOBILE = (463, 625)
CARD = (362, 453)
GAP = 24
MARGIN = {"desktop": (56, 45), "mobile": (28, 35)}  # (horizontal, vertical) working values
BRAND_ZONE = 0.30  # desktop: left ~30% is the brand zone, cards start after it


def dashed_rect(draw, box, color, dash=10):
    x0, y0, x1, y1 = box
    for x in range(x0, x1, dash * 2):
        draw.line([(x, y0), (min(x + dash, x1), y0)], fill=color, width=2)
        draw.line([(x, y1), (min(x + dash, x1), y1)], fill=color, width=2)
    for y in range(y0, y1, dash * 2):
        draw.line([(x0, y), (x0, min(y + dash, y1))], fill=color, width=2)
        draw.line([(x1, y), (x1, min(y + dash, y1))], fill=color, width=2)


def load_cards(paths):
    from PIL import Image
    cards = []
    for p in paths:
        im = Image.open(p).convert("RGB")
        if im.size != CARD:
            print(f"WARN {p}: {im.size[0]}x{im.size[1]}, expected {CARD[0]}x{CARD[1]}; resized for preview", file=sys.stderr)
            im = im.resize(CARD)
        cards.append(im)
    return cards


def compose(bg_path, size, kind, cards, scroll, out_path, expect=None):
    from PIL import Image, ImageDraw
    bg = Image.open(bg_path).convert("RGB")
    if bg.size != size:
        print(f"WARN {bg_path}: {bg.size[0]}x{bg.size[1]}, expected {size[0]}x{size[1]}", file=sys.stderr)
        bg = bg.resize(size)
    canvas = bg.copy()
    w, h = size
    top = (h - CARD[1]) // 2
    start = int(w * BRAND_ZONE) + GAP if kind == "desktop" else (w - CARD[0]) // 2
    for i, card in enumerate(cards):
        x = start + i * (CARD[0] + GAP) - scroll
        if x + CARD[0] > 0 and x < w:
            shadow = Image.new("RGB", CARD, (0, 0, 0))
            canvas.paste(shadow, (x + 3, top + 4), Image.new("L", CARD, 40))
            canvas.paste(card, (x, top))
    mx, my = MARGIN[kind]
    dashed_rect(ImageDraw.Draw(canvas), (mx, my, w - mx, h - my), (0, 140, 90))
    canvas.save(out_path)
    return out_path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bg-desktop", required=True)
    ap.add_argument("--bg-mobile", required=True)
    ap.add_argument("--cards", nargs="+", required=True, help="362x453 card images, in carousel order")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    cards = load_cards(a.cards)
    step = CARD[0] + GAP
    last = max(0, len(cards) - 1)
    jobs = [
        ("desktop_first_screen", a.bg_desktop, DESKTOP, "desktop", 0),
        ("desktop_scrolled", a.bg_desktop, DESKTOP, "desktop", step),
        ("desktop_last_card", a.bg_desktop, DESKTOP, "desktop", last * step - (DESKTOP[0] - CARD[0] - GAP) + int(DESKTOP[0] * BRAND_ZONE) + GAP),
        ("mobile_first_screen", a.bg_mobile, MOBILE, "mobile", 0),
        ("mobile_last_card", a.bg_mobile, MOBILE, "mobile", last * step),
    ]
    for name, bg, size, kind, scroll in jobs:
        print(compose(bg, size, kind, cards, scroll, os.path.join(a.out, name + ".png")))
    print("Review: nothing important cropped or covered; no key text/faces behind cards; margins respected.")


if __name__ == "__main__":
    main()
