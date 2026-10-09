# QA and Preflight

Run before every final report. Fix what you can; report only what remains.

## 1. Scripted checks (deterministic)

`python scripts/validate_asset.py <file> --placement <id> [--expect WxH]`

Covers: file readable, format, color mode (RGB only for A+), file size, dimensions vs. preset/minimum, aspect ratio, MAIN white background and edge-clipping heuristics, MAIN product fill estimate, video container/codec/fps/duration/bitrate via `ffprobe` (when installed), Store/SB limits. Anything that cannot be checked deterministically is returned as `MANUAL` or `VERIFY_IN_UI`, never as PASS.

## 2. Visual checks (manual / by vision)

| Check | Pass condition |
|---|---|
| Fidelity vs. source | silhouette, proportions, logo, packaging text, cap/closure, color, orientation, unit count, included parts match the source (`product-fidelity.md`) |
| Exact text | every text block equals the approved copy character-for-character; locale spelling, units, decimal separators correct |
| Layout | matches the approved verbal wireframe; reading order works; nothing covers the product's logo/label |
| Safe zones | Store hero central safe area, tile link-title overlay, Brand Story cards/crops, A+ responsive crop respected |
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
