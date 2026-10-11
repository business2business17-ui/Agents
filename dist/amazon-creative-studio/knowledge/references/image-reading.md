# Image reading - turn pictures into design input

Use whenever an image is an INPUT to design: the product's own photos, a competitor/reference listing image, a client's mood board, a screenshot of A+ / Store, an existing creative to rework. Goal: the user never has to describe a picture in words.

## 1. Sources (all read-only)
- Files in the workspace or chat attachments (JPG/PNG/WEBP/TIFF/PDF pages/screenshots).
- Google Drive / Docs / Sheets / Slides links -> `scripts/google_link.py` (images embedded in a Doc/Slides export, Drive image files).
- Amazon links of any country (ASIN or category) -> `scripts/amazon_link.py parse|plan|open`. It identifies the marketplace/ASIN and gives the official data route (Helium 10 MCP `get_listing_details` / `retrieve_listing_by_asin` / `analyze_product_images` when connected). **No scraping or bulk download of Amazon pages.** For competitor images: use the MCP result, or ask the user to open the link (`open`) and drop screenshots/files into the chat. One-off reading of what the user shows is fine.
- Competitor material is `REFERENCE_ONLY`: you analyse composition, information hierarchy, angle set, claims, gaps - you never copy layout 1:1, copy text, icons, photos or brand cues. Record `IP_REVIEW_REQUIRED` if a plan would resemble a competitor closely.

## 2. Procedure (do it yourself, do not hand commands to the user)
1. Measure: `python scripts/image_probe.py FILE... --tiles OUT_DIR` (size, aspect, DPI, background, fill %, clipping, 3x3 zone occupancy, palette, sharpness, text-density hint). Several images: `--sheet sheet.jpg` for a side-by-side contact sheet.
2. Look: open the file with your image-viewing ability (Read on the image path). Then open the tiles (`*_tile_TL/TR/BL/BR.jpg`) to read small print, labels, fine details. If you cannot view images on this platform, say so once and ask the user for a text description of exactly the fields in section 3 - do not guess content from numbers.
3. Fill the **Visual Reading Record** (section 3) per image. Facts only; mark anything unreadable `ILLEGIBLE`, anything uncertain `UNSURE` (never fill a gap with a plausible guess).
4. Cross-check against TTX/XLSX: if the pack shows a different volume, color, count, claim than the sheet -> `DATA_IMAGE_CONFLICT` row for the checkpoint; the image never silently overrides the sheet and the sheet never silently overrides the image.
5. Derive design decisions (section 4) and carry them into the layout scheme, the brief and the prompts. Store reusable findings (palette, fonts guess, tone, protected elements) in `creative-studio/PROJECT.md`.

## 3. Visual Reading Record (one per image)
```
IMG: <file / source link> | role: product source | competitor ref | brand mood | existing creative | screenshot
Technical: <px, aspect, background kind, fill %, clipping, blur/low-res> (from image_probe)
Subject: <what exactly is shown: product, form, color/finish, count of units, accessories, in-use/lifestyle, model>
View/angle: front | back | side | 45 deg | top | detail/macro | in-hand | scene
Text on product/pack (exact transcription, language): <...> | ILLEGIBLE parts: <...>
Text/graphics on image (headline, badges, icons, infographics): <list with position>
Layout: <zones, reading order, where product sits, empty/safe areas, hierarchy>
Colors/typography/style: <palette hex from probe + names; font style guess (serif/sans/rounded...), mood>
Claims/proof visible: <claims shown, certifications, numbers> -> each needs source in data (else VERIFY / do not reuse)
Quality / fidelity risks: <glare, shadows, label curvature, crop, mirrored/AI artefacts, low-res label>
Gaps vs plan: <missing angle, missing proof, weak MAIN, no scale, no benefit>
```

## 4. What to extract per task
- **Own product images -> Product Fidelity Lock inputs:** exact shape, label text, colors, logo placement, which view is protected; which required view is missing (ask for the real image or create environment only).
- **Competitor / reference images -> gap analysis:** how many images, which angles and benefits they show, order of information, what proof they show, what is missing -> opportunities for the user's own, different concept. Never "make it like this one" literally.
- **Mood board / brand images -> style tokens:** palette, type feel, lighting, props, background family, margins; write them as tokens in PROJECT.md.
- **Existing creative to rework -> change list:** what to keep, what violates rules (text on MAIN, clipped product, wrong size, weak mobile legibility), what to replace; produce the corrected plan row per asset.
- **Screenshot of a page -> placement map:** which module/placement it is, visible dimensions, safe areas, how copy interacts with Amazon native text.

## 5. Hard rules
- Never state a reading as fact when it is not: transcribe only what is legible at tile zoom; otherwise `ILLEGIBLE` / `UNSURE`.
- Never infer ingredients, certificates, dimensions, materials or performance from a picture. Images show appearance only; facts come from the data.
- Faces/people: describe role and pose (model, age group, expression, clothing), never identify anyone; do not reuse a real person's likeness from a reference.
- Private account pages (Seller Central, orders, carts) are not read; a screenshot the user explicitly provides of their own listing is allowed.
