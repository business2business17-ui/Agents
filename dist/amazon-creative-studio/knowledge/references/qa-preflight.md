# QA and Preflight

Run before every final report. Fix what you can; report only what remains.

## 1. Scripted checks (deterministic)

`python scripts/validate_asset.py <file> --placement <id> [--expect WxH]`

Covers: file readable, format, color mode (RGB only for A+), file size, dimensions vs. preset/minimum, aspect ratio, MAIN white background and edge-clipping heuristics, MAIN product fill estimate, video container/codec/fps/duration/bitrate via `ffprobe` (when installed), Store/SB limits. Anything that cannot be checked deterministically is returned as `MANUAL` or `VERIFY_IN_UI`, never as PASS.

Placement ids now include `pdp-main`/`pdp-secondary` (<= 10 MB, >= 2000x2000 recommended, 4000x4000 preset, sRGB, >= 72 dpi), `aplus-comparison` (150x300), `brand-story-bg` (1464x625), `brand-story-card` (362x453), `brand-story-bg-mobile` (463x625), `brand-story-logo` (315x145), `brand-story-asin` (166x182). After preflight passes, pack the carousel with `scripts/pack_upload_zip.py` (ASIN naming).

### File-size rule (carousel, <= 10 MB)

A 4000x4000 file over 10 MB is fixed by **compression, not by fewer pixels**: re-export as optimized JPEG (quality ~85-92, progressive, sRGB, metadata stripped) and re-run the validator. Only if it still does not fit, **stop and warn the user**: state the current size, the pixel size you propose (never below 2000x2000, the Amazon recommended floor) and the reason; reduce pixels only after the user agrees, and record it in the workbook `ISSUES` sheet. Never reduce silently.

### PT slots

The number of PT slots per category is `VERIFY_IN_UI`. The agent plans MAIN + 6 (PT01-PT06); `pack_upload_zip.py` accepts up to 8 and prints the same label. Say in the final report that the slot count was not verified for the category.

## 2. Visual checks (manual / by vision)

| Check | Pass condition |
|---|---|
| Fidelity vs. source | silhouette, proportions, logo, packaging text, cap/closure, color, orientation, unit count, included parts match the source (`product-fidelity.md`) |
| Exact text | every text block equals the approved copy character-for-character; locale spelling, units, decimal separators correct |
| Layout | matches the approved verbal wireframe; reading order works; nothing covers the product's logo/label |
| Safe zones | Store hero central safe area, tile link-title overlay, Brand Story cards/crops, A+ responsive crop respected |
| Brand Story | separate Desktop (1464x625) and Mobile (463x625) previews built (`scripts/brand_story_preview.py`); cards over background checked on first screen, scroll and extreme positions; nothing important cropped/covered; no key text/faces behind cards; background has no baked-in cards; Mobile is its own composition; sizes rechecked against the current Seller Central uploader |
| Mobile | text legible at phone display size (approx. 375 px wide preview) |
| Claims | every claim traceable to a supplied fact; no strengthened translation; no invented award/cert/comparison |
| Policy | MAIN rules; no watermark, QR code, hyperlink, HTML, animated GIF in A+; language matches the selected content language |

## 3. Status

Per asset, then overall:

- `READY FOR AMAZON CREATIVE UPLOAD` - all required checks PASS; only informational `VERIFY_IN_UI` notes remain that are not blocking.
- `READY AFTER USER-APPROVED CROP/EXPORT` - content correct, a mechanical crop/resize/format change is needed and the user must approve it.
- `NOT READY FOR AMAZON CREATIVE UPLOAD` - any failed check, any unauthorized product mismatch, or any unverified production-critical spec.

Each `NOT READY` line: `asset - placement - issue - exact correction - who (agent/user)`.

Write failures to the workbook `ISSUES` sheet.
