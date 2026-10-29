# Image and text clarity: production and Amazon acceptance

This mandatory internal `PRODUCTION_PRESET` applies to **listing carousel (MAIN and secondary images), Brand Story, Brand Store, A+ Premium and A+ Basic**. Include it in every designer brief and AI production prompt, including standalone handoffs. Passing dimensions, format and file-weight checks alone does not establish visual quality.

The goal is clear product details, clean graphics and readable approved text at the actual shopper display size, including after upload and Amazon processing. Do not promise zero recompression or identical pixels: inspect the final Amazon-rendered result. Do not diagnose an existing blurry image without comparing its source, export and rendered version.

## 1. Sources and editable master

- Use high-quality original product photographs, original logos and vector graphics. Do not use thumbnails, screenshots, messenger-compressed copies or previously compressed exports as masters.
- Inspect the protected product and label at the intended output scale. Enlarging a small source, changing DPI metadata or asking for "4K/8K/ultra sharp" does not restore missing detail. Flag an insufficient source and request a better original; never invent label text or product texture.
- Keep an editable master with separate product, background, vector graphics and live text layers. A larger working canvas is optional when the source supports it; it is not an instruction to upload oversized files.
- Preserve Product Fidelity Lock. Do not sharpen, denoise or regenerate the protected product in a way that changes packaging, letters, texture or color. Background depth of field is allowed; the product and marketing text must remain in focus.

## 2. Typography and layout that survive reduction

- Prefer native Amazon text fields where the selected module supports the required copy; verify that the text also appears on mobile. Never add marketing text to MAIN.
- For embedded marketing text, generate the scene first, then typeset the exact approved copy with a deterministic text/compositing tool. Keep letters and icons editable/vector until final raster export; do not depend on generated lettering for the final asset.
- Use a clear font with sufficient stroke weight, strong text/background contrast and a quiet text zone. Avoid thin/light fonts, tiny footnotes, narrow letter spacing, hairline graphics and small saturated colored type that degrades when reduced. Simplify or split dense copy across assets; do not shrink it to make it fit.
- Define font sizes at the displayed image scale. Internal starting targets: body/callouts at least **16 px**, headline at least **24 px** at intended mobile display size; key graphic strokes about **2 displayed px** or more. These are production targets, **not Amazon requirements**; inspect the actual font, module and crop.
- Estimate scaling with `displayed text px = export text px * displayed image width / exported image width`. For a crop/card use that asset's actual rendered scale, not the page width. Check at 375 px and 430 px viewport widths as internal preview presets, plus the actual Amazon mobile layout when accessible.
- Provide a separate mobile composition/export where supported if the desktop layout cannot remain readable. Preserve approved copy and product proportions.

## 3. Export without avoidable quality loss

- Record placement/module, marketplace, upload pixel box, aspect ratio, accepted format and file-weight limit from the current builder or verified specification, with source/date and requirement labels. Unknown production-critical values stay `VERIFY_IN_UI`.
- Export at the approved upload size in sRGB. Keep the carousel's existing 4000 x 4000 preset; for A+ Basic, A+ Premium, Brand Story and Store use the selected module's own verified upload specification. Do not reuse one dimension everywhere or upload 2x/4x files assuming Amazon will preserve them.
- Resize from the editable master once with high-quality resampling; rasterize text/graphics at final pixel size. Never stretch images, repeatedly resize flattened text or repeatedly save JPEGs. DPI metadata is not a substitute for pixel resolution.
- Where accepted, prefer lossless PNG for text-heavy layouts, line art and flat graphics if it fits the limit. Use high-quality JPEG for photographs or when required by the uploader/file-weight budget. Internal JPEG starting point: quality 90-95, with 4:4:4 chroma sampling for embedded text/colored edges when supported. Encoder scales vary; inspect and adjust within the placement limit. These are presets, not Amazon mandates or guarantees.
- Optimize weight without visible damage. Strip unnecessary metadata while retaining/embedding sRGB information; use lossless optimization where useful. Compare edges and letters after compression changes. Reject blur, ringing, blocks, color bleeding and broken strokes.
- Use only restrained output sharpening after resizing where needed and without altering the protected product. Reject halos and brittle edges. Replace a weak source instead of cosmetically declaring it sharp.
- If quality and file-weight constraints cannot both pass, revise background detail or approved layout/text density, or obtain a better source. Follow the existing approval rule before reducing carousel pixels. Never silently relax quality to pass the validator.

## 4. Placement-specific checks

| Placement | Required clarity check |
|---|---|
| Listing carousel | MAIN product edges/details remain natural and focused; no added text. Secondary-image headlines, callouts and icons remain readable in the normal mobile gallery without zoom. |
| Brand Story | Inspect background and foreground cards separately, including mobile crops and overlays; essential text/branding must not disappear beneath cards. |
| Brand Store | Inspect hero and each tile at their own desktop/mobile scale; prefer native text and verify essential copy in any custom mobile layout. |
| A+ Premium | Check each selected module and separate mobile asset; larger banners must not justify smaller displayed copy. Inspect carousel/hotspot overlays where used. |
| A+ Basic | Check each selected module at actual display size; simplify small comparison images and dense layouts, using available native text fields. Do not copy Premium dimensions. |

## 5. Two-stage QA and acceptance

Record **both** results per asset; a technical validator cannot certify visual clarity.

1. `LOCAL_CLARITY_QA = PASS / FAIL`: inspect the final upload file at 100% pixels for defects and at actual desktop/mobile display size for readability. Compare with the original; check exact copy, letter edges, product fidelity, graphic strokes, crops and safe zones. Save export settings and preview evidence. A locally downscaled/recompressed preview is a stress test, not proof of Amazon's processing.
2. `AMAZON_RENDER_QA = PASS / FAIL / NOT_CHECKED`: after an authorized upload has finished processing and fully loaded, inspect Amazon's desktop/mobile preview. Inspect the live customer-facing page when available; record evidence scope as `BUILDER_PREVIEW` or `LIVE_PAGE`. A preview-only pass keeps live verification pending. Capture asset/version, marketplace/module, date, page/preview reference, viewport/device and screenshots where possible.

Acceptance: intended marketing copy is readable without zoom; letters/icons do not merge or bleed; no visible blocks, halos or soft focus at normal display size; product details remain faithful and are not degraded by production. Do not require microscopic physical label text to be readable in a thumbnail.

If Amazon QA fails, compare source -> export -> Amazon-rendered image; identify source, export, text-scale, crop or rendering issues; revise from the master, re-export and recheck through the authorized upload workflow. Do not repeatedly re-save the uploaded JPEG.

If access, upload authorization or a live page is unavailable, mark the relevant check `NOT_CHECKED`, stating why and what must be checked next. Do not upload/publish solely to complete this checklist without authorization. `READY FOR AMAZON CREATIVE UPLOAD` may mean local QA passed and upload can proceed; it **never** means post-upload clarity passed. Failed local QA blocks upload readiness; failed Amazon QA blocks final acceptance.

## 6. Mandatory block in every brief and AI prompt

Include this block in full, translate as needed and fill its per-asset values. A reference link alone is insufficient for a standalone handoff.

```text
IMAGE AND TEXT CLARITY — REQUIRED PRODUCTION QUALITY
Placement/module: [carousel / Brand Story / Brand Store / A+ Premium / A+ Basic; exact module].
Upload export: [W x H px, aspect, accepted format, sRGB, file-weight limit, verified source/date].
Keep the product, graphics and approved text clear at actual desktop/mobile size; verify again after Amazon upload/processing. Technical acceptance alone is not visual acceptance.
Use high-quality originals and an editable layered master. Do not enlarge a poor source and present it as restored detail; never redraw product/label details.
Typeset exact approved copy in native Amazon fields where supported, otherwise deterministic editable text layers rasterized at final size. MAIN has no added marketing text.
Displayed text/graphics: [font, weight, export px -> displayed px, contrast, stroke width, mobile layout/crop]. No tiny/thin type or crowded copy.
Resize once from the master. Use lossless PNG for text/graphics if accepted and within limit, otherwise visually checked high-quality JPEG; avoid repeated JPEG saves and aggressive compression/sharpening.
Export settings: [format, quality/chroma sampling if applicable, resampling, profile, final bytes].
LOCAL_CLARITY_QA: [PASS / FAIL; evidence at 100% and desktop/mobile display size].
AMAZON_RENDER_QA: [PASS / FAIL / NOT_CHECKED; BUILDER_PREVIEW / LIVE_PAGE; device/viewport, date, evidence or reason pending].
Deliver the editable master, final upload file, previews and QA record. If text blurs, edges bleed or product detail deteriorates, revise and recheck. Never claim post-upload success without inspecting the Amazon-rendered result.
```

## Requirement boundaries

Placement limits remain governed by `amazon-specs.md` and current official sources/the selected Amazon builder. The typography targets, export settings and two-stage QA above are internal production standards, not additional verified Amazon requirements. Do not copy Store guidance into A+ modules or infer universal uploader limits.
