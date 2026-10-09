#!/usr/bin/env python3
"""Deterministic technical preflight for Amazon creative assets.

Usage:
  validate_asset.py FILE --placement ID [--expect WxH] [--json]
  validate_asset.py --list-placements

Exit codes: 0 = no failures and no warnings, 1 = at least one FAIL, 2 = warnings only.

Every check returns PASS / FAIL / WARN / MANUAL / VERIFY_IN_UI together with the
requirement status (AMAZON_REQUIRED / AMAZON_RECOMMENDED / PRODUCTION_PRESET).
Checks that cannot be done deterministically are MANUAL or VERIFY_IN_UI, never PASS.
Specs mirror references/amazon-specs.md; keep both in sync.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

MB = 1024 * 1024

# id -> spec. Keys: kind, formats, rgb_only, max_bytes, min (w,h), exact (w,h),
# aspect (min,max) as w/h floats, square, notes.
PLACEMENTS = {
    "pdp-main": dict(kind="image", formats={"JPEG", "PNG", "TIFF"}, min_long_side=1000,
                     preset=(4000, 4000), square=True, main=True,
                     notes="Pure white background, real product, no text/graphics, fill >=85%."),
    "pdp-secondary": dict(kind="image", formats={"JPEG", "PNG", "TIFF"}, min_long_side=1000,
                          preset=(4000, 4000), square=True,
                          notes="Preset 4000x4000 1:1 is PRODUCTION_PRESET, not an Amazon mandate."),
    "aplus-basic": dict(kind="image", formats={"JPEG", "PNG", "BMP"}, rgb_only=True,
                        max_bytes=2 * MB, min_dpi=72,
                        notes="Module image box is VERIFY_IN_UI (970x300 is only the general comparison size)."),
    "aplus-premium": dict(kind="image", formats={"JPEG", "PNG", "BMP"}, rgb_only=True,
                          max_bytes=2 * MB, min_dpi=72,
                          notes="Module image box is VERIFY_IN_UI (1464x600 is only the general comparison size)."),
    "brand-story": dict(kind="image", formats={"JPEG", "PNG", "BMP"}, rgb_only=True,
                        max_bytes=2 * MB, min_dpi=72,
                        notes="Background/card pixel sizes are VERIFY_IN_UI for the account/marketplace."),
    "store-hero": dict(kind="image", formats={"JPEG", "PNG"}, min=(3000, 600), max_bytes=5 * MB,
                       notes="Amazon may crop up to 30% (15% per side); keep content central."),
    "store-logo": dict(kind="image", formats={"JPEG", "PNG"}, min=(400, 400), max_bytes=5 * MB),
    "store-tile-full": dict(kind="image", formats={"JPEG", "PNG"}, min=(1500, 20), max_bytes=5 * MB,
                            notes="3000 px width recommended; bottom ~19% can be hidden by link title."),
    "store-tile-large": dict(kind="image", formats={"JPEG", "PNG"}, min=(1500, 1500), max_bytes=5 * MB,
                             notes="Bottom ~12% can be hidden by link title."),
    "store-tile-medium": dict(kind="image", formats={"JPEG", "PNG"}, min=(1500, 750), max_bytes=5 * MB,
                              notes="Bottom ~19% can be hidden by link title."),
    "store-tile-small": dict(kind="image", formats={"JPEG", "PNG"}, min=(750, 750), max_bytes=5 * MB,
                             notes="Bottom ~12% can be hidden by link title."),
    "store-gallery": dict(kind="image", formats={"JPEG", "PNG"}, min=(1500, 750), max_bytes=5 * MB),
    "sb-video": dict(kind="video", containers={"mp4", "mov"}, sizes={(1280, 720), (1920, 1080), (3840, 2160)},
                     dur=(6, 45), dur_rec=20, max_bytes=500 * MB, vcodecs={"h264", "hevc"},
                     fps={23.976, 23.98, 24, 25, 29.97, 29.98, 30}, min_vbitrate=1_000_000,
                     acodecs={"pcm_s16le", "pcm_s24le", "pcm_s32le", "aac", "mp3"},
                     min_abitrate=96_000, min_asample=44100, aspect=16 / 9),
    "store-video": dict(kind="video", containers={"mp4", "mov"}, vcodecs={"h264"},
                        notes="Tile-specific resolution and aspect range: see amazon-specs.md section 6."),
    "listing-video": dict(kind="video", containers={"mp4", "mov"},
                          notes="Listing-video limits are VERIFY_IN_UI (do not reuse SB video specs)."),
}


def res(check, status, req, detail):
    return dict(check=check, status=status, requirement=req, detail=detail)


def parse_wh(s):
    w, h = s.lower().split("x")
    return int(w), int(h)


def check_image(path, spec, expect, results):
    try:
        from PIL import Image
    except ImportError:
        results.append(res("pillow", "FAIL", "TOOLING", "Pillow is required: pip install Pillow"))
        return
    try:
        im = Image.open(path)
        im.load()
    except Exception as e:  # noqa: BLE001
        results.append(res("readable", "FAIL", "AMAZON_REQUIRED", f"cannot open image: {e}"))
        return
    results.append(res("readable", "PASS", "AMAZON_REQUIRED", "image opens"))
    w, h = im.size
    fmt = im.format
    results.append(res("dimensions", "INFO", "-", f"{w}x{h} px, aspect {w / h:.4f}, format {fmt}, mode {im.mode}"))

    if "formats" in spec:
        ok = fmt in spec["formats"]
        results.append(res("format", "PASS" if ok else "FAIL", "AMAZON_REQUIRED",
                           f"{fmt} (allowed: {', '.join(sorted(spec['formats']))})"))
    if spec.get("rgb_only"):
        ok = im.mode in ("RGB", "RGBA", "P", "L")
        cmyk = im.mode == "CMYK"
        results.append(res("colorspace", "FAIL" if cmyk else ("PASS" if ok else "WARN"), "AMAZON_REQUIRED",
                           f"mode {im.mode}; A+ requires RGB, CMYK is rejected"))
    if "max_bytes" in spec:
        size = os.path.getsize(path)
        ok = size <= spec["max_bytes"]
        results.append(res("file_size", "PASS" if ok else "FAIL", "AMAZON_REQUIRED",
                           f"{size / MB:.2f} MB (max {spec['max_bytes'] / MB:.0f} MB)"))
    if "min_dpi" in spec:
        dpi = im.info.get("dpi")
        if dpi and min(dpi) >= spec["min_dpi"] - 0.5:
            results.append(res("dpi", "PASS", "AMAZON_REQUIRED", f"dpi {dpi}"))
        elif dpi:
            results.append(res("dpi", "FAIL", "AMAZON_REQUIRED", f"dpi {dpi} < {spec['min_dpi']}"))
        else:
            results.append(res("dpi", "WARN", "AMAZON_REQUIRED", "no dpi metadata; confirm >= 72 dpi on export"))
    if "min" in spec:
        mw, mh = spec["min"]
        ok = w >= mw and h >= mh
        results.append(res("min_dimensions", "PASS" if ok else "FAIL", "AMAZON_REQUIRED",
                           f"{w}x{h} (minimum {mw}x{mh})"))
    if "min_long_side" in spec:
        ok = max(w, h) >= spec["min_long_side"]
        results.append(res("zoom_resolution", "PASS" if ok else "WARN", "AMAZON_RECOMMENDED",
                           f"longest side {max(w, h)} px (>= {spec['min_long_side']} enables zoom)"))
    if spec.get("square"):
        results.append(res("aspect_1_1", "PASS" if w == h else "WARN", "PRODUCTION_PRESET",
                           f"{w}x{h} ({'square' if w == h else 'not 1:1; Amazon does not mandate 1:1'})"))
    if "preset" in spec:
        pw, ph = spec["preset"]
        results.append(res("preset_size", "PASS" if (w, h) == (pw, ph) else "WARN", "PRODUCTION_PRESET",
                           f"{w}x{h} (preset {pw}x{ph})"))
    if expect:
        ew, eh = expect
        results.append(res("expected_size", "PASS" if (w, h) == (ew, eh) else "FAIL", "PRODUCTION_PRESET",
                           f"{w}x{h} (expected {ew}x{eh})"))
    if spec.get("notes"):
        results.append(res("placement_note", "VERIFY_IN_UI" if "VERIFY_IN_UI" in spec["notes"] else "INFO",
                           "-", spec["notes"]))
    if spec.get("main"):
        check_main(im, results)
    results.append(res("visual_review", "MANUAL", "-",
                       "fidelity vs. source, exact text, safe zones, mobile legibility, claims: see qa-preflight.md"))


def check_main(im, results, tol=4):
    """Heuristics for the MAIN image: white background, edge clipping, product fill."""
    from PIL import Image
    rgb = im.convert("RGBA")
    if im.mode in ("RGBA", "LA", "P") and "A" in rgb.getbands():
        alpha_min = rgb.getchannel("A").getextrema()[0]
        if alpha_min < 255:
            results.append(res("main_transparency", "FAIL", "AMAZON_REQUIRED",
                               "image has transparent pixels; MAIN must be flattened on pure white"))
    flat = Image.new("RGB", rgb.size, (255, 255, 255))
    flat.paste(rgb, mask=rgb.getchannel("A"))
    w, h = flat.size
    # downscale for speed; keep thin features by using NEAREST on a max 1000 px side
    scale = 1000 / max(w, h)
    small = flat.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.NEAREST) if scale < 1 else flat
    sw, sh = small.size
    px = small.load()
    # background: border must be (near) pure white
    border = [px[x, 0] for x in range(sw)] + [px[x, sh - 1] for x in range(sw)] + \
             [px[0, y] for y in range(sh)] + [px[sw - 1, y] for y in range(sh)]
    non_white_border = sum(1 for p in border if min(p) < 255 - tol)
    corners = [px[0, 0], px[sw - 1, 0], px[0, sh - 1], px[sw - 1, sh - 1]]
    corners_white = all(min(c) >= 255 - tol for c in corners)
    if not corners_white:
        results.append(res("main_background", "FAIL", "AMAZON_REQUIRED",
                           f"corner pixels not pure white: {corners}"))
    else:
        results.append(res("main_background", "PASS", "AMAZON_REQUIRED",
                           "corners are pure white (tolerance +/-%d); full-image background uniformity still needs a visual check" % tol))
    # bounding box of non-white content
    xs0, ys0, xs1, ys1 = sw, sh, -1, -1
    for y in range(sh):
        for x in range(sw):
            if min(px[x, y]) < 255 - tol:
                if x < xs0: xs0 = x
                if x > xs1: xs1 = x
                if y < ys0: ys0 = y
                if y > ys1: ys1 = y
    if xs1 < 0:
        results.append(res("main_product_present", "FAIL", "AMAZON_REQUIRED", "image is entirely white"))
        return
    bw, bh = (xs1 - xs0 + 1) / sw, (ys1 - ys0 + 1) / sh
    fill = max(bw, bh)
    results.append(res("main_fill", "PASS" if fill >= 0.85 else "FAIL", "AMAZON_REQUIRED",
                       f"content bounding box spans {bw * 100:.1f}% x {bh * 100:.1f}% of the frame; "
                       f"longest span {fill * 100:.1f}% (>= 85% required; preset target 85-90%). "
                       "Estimate includes shadows - confirm visually."))
    if fill > 0.90:
        results.append(res("main_fill_target", "WARN", "PRODUCTION_PRESET",
                           f"longest span {fill * 100:.1f}% > 90% preset target; check margins / clipping"))
    touches = [n for n, v in (("left", xs0 == 0), ("right", xs1 == sw - 1),
                              ("top", ys0 == 0), ("bottom", ys1 == sh - 1)) if v]
    results.append(res("main_edge_clipping", "WARN" if touches else "PASS", "AMAZON_REQUIRED",
                       ("non-white content touches " + "/".join(touches) + " edge: product may be clipped")
                       if touches else "no content touches the frame edge"))
    results.append(res("main_no_text_graphics", "MANUAL", "AMAZON_REQUIRED",
                       "no text, badges, borders, watermarks, extra props: visual check"))


def ffprobe(path):
    exe = shutil.which("ffprobe")
    if not exe:
        return None
    out = subprocess.run([exe, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path],
                         capture_output=True, text=True)
    if out.returncode != 0:
        return {"error": out.stderr.strip()}
    return json.loads(out.stdout)


def fps_of(stream):
    try:
        n, d = stream.get("avg_frame_rate", "0/1").split("/")
        return round(float(n) / float(d), 3) if float(d) else 0.0
    except Exception:  # noqa: BLE001
        return 0.0


def check_video(path, spec, expect, results):
    info = ffprobe(path)
    if info is None:
        results.append(res("ffprobe", "WARN", "TOOLING",
                           "ffprobe not installed; technical video specs could not be checked (MANUAL)"))
        return
    if "error" in info:
        results.append(res("readable", "FAIL", "AMAZON_REQUIRED", f"ffprobe error: {info['error']}"))
        return
    results.append(res("readable", "PASS", "AMAZON_REQUIRED", "video parses"))
    fmt = info.get("format", {})
    streams = info.get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video"), None)
    a = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if not v:
        results.append(res("video_stream", "FAIL", "AMAZON_REQUIRED", "no video stream"))
        return
    w, h = v.get("width", 0), v.get("height", 0)
    dur = float(fmt.get("duration") or v.get("duration") or 0)
    size = os.path.getsize(path)
    fps = fps_of(v)
    results.append(res("stream_info", "INFO", "-",
                       f"{w}x{h}, {v.get('codec_name')}, {fps} fps, {dur:.1f}s, {size / MB:.1f} MB, profile {v.get('profile')}"))
    ext = os.path.splitext(path)[1].lstrip(".").lower()
    if "containers" in spec:
        results.append(res("container", "PASS" if ext in spec["containers"] else "FAIL", "AMAZON_REQUIRED",
                           f".{ext} (allowed: {', '.join(sorted(spec['containers']))})"))
    if "vcodecs" in spec:
        c = v.get("codec_name")
        results.append(res("video_codec", "PASS" if c in spec["vcodecs"] else "FAIL", "AMAZON_REQUIRED",
                           f"{c} (allowed: {', '.join(sorted(spec['vcodecs']))})"))
    if "sizes" in spec:
        results.append(res("resolution", "PASS" if (w, h) in spec["sizes"] else "FAIL", "AMAZON_REQUIRED",
                           f"{w}x{h} (allowed: {', '.join(f'{a}x{b}' for a, b in sorted(spec['sizes']))})"))
    if "aspect" in spec and h:
        ok = abs(w / h - spec["aspect"]) < 0.01
        results.append(res("aspect_16_9", "PASS" if ok else "FAIL", "AMAZON_REQUIRED", f"{w / h:.3f}"))
    if "dur" in spec:
        lo, hi = spec["dur"]
        results.append(res("duration", "PASS" if lo <= dur <= hi else "FAIL", "AMAZON_REQUIRED",
                           f"{dur:.1f}s (allowed {lo}-{hi}s)"))
        if dur > spec.get("dur_rec", hi):
            results.append(res("duration_recommended", "WARN", "AMAZON_RECOMMENDED",
                               f"{dur:.1f}s > recommended {spec['dur_rec']}s"))
    if "max_bytes" in spec:
        results.append(res("file_size", "PASS" if size <= spec["max_bytes"] else "FAIL", "AMAZON_REQUIRED",
                           f"{size / MB:.1f} MB (max {spec['max_bytes'] / MB:.0f} MB)"))
    if "fps" in spec:
        ok = any(abs(fps - f) < 0.02 for f in spec["fps"])
        results.append(res("frame_rate", "PASS" if ok else "FAIL", "AMAZON_REQUIRED", f"{fps} fps"))
    if "min_vbitrate" in spec:
        br = int(v.get("bit_rate") or fmt.get("bit_rate") or 0)
        if br:
            results.append(res("video_bitrate", "PASS" if br >= spec["min_vbitrate"] else "FAIL",
                               "AMAZON_REQUIRED", f"{br / 1e6:.2f} Mbps (min 1, 4+ recommended)"))
        else:
            results.append(res("video_bitrate", "WARN", "AMAZON_REQUIRED", "bitrate not reported"))
    if v.get("field_order") not in (None, "progressive", "unknown"):
        results.append(res("scan", "FAIL", "AMAZON_REQUIRED", f"field_order {v.get('field_order')}; must be progressive"))
    if "acodecs" in spec:
        if not a:
            results.append(res("audio", "WARN", "AMAZON_RECOMMENDED", "no audio stream"))
        else:
            ok = a.get("codec_name") in spec["acodecs"]
            results.append(res("audio_codec", "PASS" if ok else "FAIL", "AMAZON_REQUIRED", str(a.get("codec_name"))))
            sr = int(a.get("sample_rate") or 0)
            results.append(res("audio_sample_rate", "PASS" if sr >= spec["min_asample"] else "FAIL",
                               "AMAZON_REQUIRED", f"{sr} Hz (min {spec['min_asample']})"))
            abr = int(a.get("bit_rate") or 0)
            if abr:
                results.append(res("audio_bitrate", "PASS" if abr >= spec["min_abitrate"] else "FAIL",
                                   "AMAZON_REQUIRED", f"{abr / 1000:.0f} kbps (min 96)"))
    if expect:
        results.append(res("expected_size", "PASS" if (w, h) == expect else "FAIL", "PRODUCTION_PRESET",
                           f"{w}x{h} (expected {expect[0]}x{expect[1]})"))
    if spec.get("notes"):
        results.append(res("placement_note", "VERIFY_IN_UI", "-", spec["notes"]))
    results.append(res("visual_review", "MANUAL", "-",
                       "product identity frame-to-frame, embedded text, claims: see qa-preflight.md"))


def overall(results):
    s = {r["status"] for r in results}
    if "FAIL" in s:
        return "NOT READY FOR AMAZON CREATIVE UPLOAD", 1
    if "WARN" in s:
        return "READY AFTER USER-APPROVED CROP/EXPORT (resolve warnings; manual checks still required)", 2
    return "TECHNICAL CHECKS PASSED - complete MANUAL/VERIFY_IN_UI items before READY FOR AMAZON CREATIVE UPLOAD", 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", nargs="?")
    ap.add_argument("--placement", help="placement id (see --list-placements)")
    ap.add_argument("--expect", help="expected size WxH, e.g. 4000x4000")
    ap.add_argument("--json", action="store_true", help="print JSON only")
    ap.add_argument("--list-placements", action="store_true")
    a = ap.parse_args()

    if a.list_placements:
        for k, v in PLACEMENTS.items():
            print(f"{k:18} {v['kind']}")
        return 0
    if not a.file or not a.placement:
        ap.error("FILE and --placement are required")
    if a.placement not in PLACEMENTS:
        ap.error(f"unknown placement '{a.placement}'. Use --list-placements")
    if not os.path.isfile(a.file):
        print(f"file not found: {a.file}", file=sys.stderr)
        return 1
    spec = PLACEMENTS[a.placement]
    expect = parse_wh(a.expect) if a.expect else None
    results = []
    (check_image if spec["kind"] == "image" else check_video)(a.file, spec, expect, results)
    status, code = overall(results)
    out = dict(file=a.file, placement=a.placement, overall=status, checks=results)
    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(f"{a.file}  [{a.placement}]")
        for r in results:
            print(f"  {r['status']:13} {r['check']:22} {r['requirement']:20} {r['detail']}")
        print(f"OVERALL: {status}")
    return code


if __name__ == "__main__":
    sys.exit(main())
