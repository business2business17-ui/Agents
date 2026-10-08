# Amazon Creative Specifications Reference

Source status: carried over from the original skill package (last stamped 2026-10-08). Not re-verified against live Amazon pages in this revision (Seller Central requires login). For any production-critical dimension, safe zone, video limit or module availability, re-check the official source or the live builder and record the date in project memory.

Use official Amazon sources first. Values may differ by marketplace, category, account eligibility, or builder version. Exact module boxes shown in the current Amazon UI take precedence over this static reference.

## Status legend

- **REQUIRED**: explicit Amazon requirement.
- **RECOMMENDED**: explicit Amazon recommendation.
- **PRESET**: internal production standard, not universal Amazon requirement.
- **VERIFY_IN_UI**: confirm in the current builder before final export.

## 1. PDP listing images

Official Seller Central image requirements include:

- MAIN background: pure white `#FFFFFF / RGB 255,255,255` — REQUIRED.
- MAIN must show the actual product; external text/logos/watermarks/graphics are prohibited — REQUIRED.
- Product should occupy at least about 85% of image area — REQUIRED in applicable image guidance.
- High-resolution image at least 1000 px in height or width enables zoom — Amazon guidance.
- Amazon does not universally mandate a 1:1 aspect ratio for product images.
- Product color must match the item for sale.
- Product must not be clipped by frame edge in MAIN.

Internal production preset requested by user:

- `4000 x 4000 px` — PRESET.
- `1:1` — PRESET.
- MAIN target fill `85-90%` while fully visible — PRESET aligned with Amazon minimum fill guidance.

Source: Amazon Seller Central Help, Product image requirements, reference G200498950; Amazon Seller Forums responses linking the same help guidance.

## 2. PDP listing video

`VERIFY_IN_UI` for the exact current listing-video uploader, category, marketplace, and account. Do not copy Sponsored Brands Video specs into listing video by assumption.

## 3. 3D product models / AR

Amazon supports 3D product experiences for eligible products/categories. Build from accurate product references and real-world dimensions. GLB/GLTF are common accepted workflow formats in Amazon 3D experiences and tooling, but final eligibility and uploader requirements are `VERIFY_IN_UI`.

Production requirements for this skill:

- match reference photography;
- preserve scale and proportions;
- preserve materials/textures/colors;
- preserve label/logo placement;
- include accurate real-world dimensions;
- no geometry simplification that changes visible product identity.

Source: Amazon Sell, 3D/AR product experiences and associated 3D workflow documentation.

## 4. A+ Content general

Official Seller Central A+ comparison:

| Content type | General image size shown by Amazon | Modules on detail page | Module selection | Video/hotspot | Navigation carousel |
|---|---:|---:|---:|---|---|
| Basic A+ | 970 x 300 px | 5 | 14 | No | No |
| Premium A+ | 1464 x 600 px | 7 | 19 | Yes | Yes |

Interpret these as Amazon's Basic-vs-Premium comparison image sizes, not proof that every individual module image box uses that exact dimension.

General A+ technical requirements:

- formats: JPG, BMP, PNG;
- RGB colorspace only;
- under 2 MB per image;
- minimum 72 dpi;
- content language must match selected content language, with limited exceptions for brand identity;
- no animated GIFs;
- no HTML tags;
- no CMYK;
- no watermarks;
- no QR codes;
- no hyperlinks/external redirects.

Amazon states oversized images may be resized to the maximum listed for a selected template box; users can crop/scale in the builder.

Source: Amazon Seller Central Help, A+ Content, references G202102930 and GLG4RQK2Y2RJADU4.

### Basic A+ modules

Exact image boxes: `VERIFY_IN_UI` for the selected module.

For comparison tables with micro images:
- use the image box dimension presented by the chosen comparison module;
- keep product recognizable at small mobile display size;
- use protected real product crop, no regenerated packaging.

### Premium A+ modules

Premium supports richer media including multiple videos, hotspot modules, enhanced comparison charts, larger images, carousel/navigation modules, and Q&A where eligible.

Exact image/video boxes: `VERIFY_IN_UI` per selected module.

## 5. A+ Brand Story

Amazon describes Brand Story as a separate A+ type appearing in the "From the brand" area. It supports one module with up to 19 preformatted cards in a carousel format, full-screen backgrounds, image/text cards, and links to products/Brand Stores.

Rules for this skill:

- create the large carousel background separately from foreground cards;
- account for desktop and mobile behavior;
- place critical branding/product details where foreground cards and responsive cropping will not hide them;
- use exact background/card pixel dimensions from the current Amazon Brand Story builder for that account/marketplace;
- do not promote third-party template dimensions to REQUIRED without current official verification.

Exact background/card pixels: `VERIFY_IN_UI`.

Source: Amazon Seller Central Help, A+ Content reference GLG4RQK2Y2RJADU4.

## 6. Brand Store

Official Amazon Ads Store creative guidelines.

### Header

| Element | Minimum image size | Max file size | Status |
|---|---:|---:|---|
| Hero image | 3000 x 600 px | 5 MB | REQUIRED minimum |
| Brand logo | 400 x 400 px | 5 MB | REQUIRED minimum |

Hero safe zone:

- Amazon may crop up to 30% total, including up to 15% from each left/right side.
- Keep all vital content in the central safe area.

### Image tiles

| Tile | Desktop minimum | Custom mobile minimum | Max file |
|---|---:|---:|---:|
| Full width | 1500 x 20 px* | 1680 x 20 px* | 5 MB |
| Large | 1500 x 1500 px | 1680 x 20 px* | 5 MB |
| Medium | 1500 x 750 px | 1680 x 20 px* | 5 MB |
| Small | 750 x 750 px | 750 x 750 px | 5 MB |

`*` Amazon recommends 3000 px image width for high-resolution display. If an image tile title is added, minimum image height is 32 px.

Link-title obscuration:

- rectangle image tiles (medium/full-width): about 19% of bottom can be obscured;
- square image tiles (small/large): about 12% of bottom can be obscured.

Amazon discourages embedded text in Store images when native text can be used, because embedded text is less accessible and not readable by search engines/screen readers.

### Image with text tile

| Layout | Full width | Large | Medium | Small |
|---|---:|---:|---:|---:|
| Text over image | 3000 x 1500 | 1500 x 1500 | 1500 x 750 | 750 x 750 |
| Text next to image | 1500 x 1500 | 1500 x 1500 | 750 x 750 | 750 x 750 |

### Shoppable image

| Tile | Minimum image |
|---|---:|
| Full width | 1500 x 750 px; 3000 x 1500 recommended for high-res |
| Large | 1500 x 1500 px |
| Medium | 1500 x 750 px |
| Small | 750 x 750 px |

### Video tile

| Tile | Minimum cover | Minimum video resolution | Aspect ratio range | Format |
|---|---:|---:|---|---|
| Full width | 3000 x 1500 | 1280 x 640 | 6:4 to 8:3 | MP4, H.264 |
| Large | 1500 x 1500 | 640 x 640 | 3:4 to 4:3 | MP4, H.264 |
| Medium | 1500 x 750 | 450 x 320 | 6:4 to 8:3 | MP4, H.264 |

### Background video tile

| Tile | Minimum video resolution | Max height | Duration | Aspect ratio range | Format |
|---|---:|---:|---|---|---|
| Full width | 1280 x 640 | 1500 px | 2-20 sec | 6:4 to 8:3 | MP4, H.264 |
| Large | 1280 x 640 | 640 px | 2-20 sec | 3:4 to 8:3 | MP4, H.264 |
| Medium | 1280 x 640 | 320 px | 2-20 sec | 6:4 to 8:3 | MP4, H.264 |

### Gallery

- Minimum image: 1500 x 750 px.
- Up to 8 images in the gallery section.

Source: Amazon Ads, Stores creative guidelines / ad specs.

## 7. Sponsored Brands Video

Official Amazon Ads requirements:

- duration: 6-45 sec; 20 sec or less highly recommended;
- dimensions: 1280 x 720, 1920 x 1080, or 3840 x 2160 px;
- max file: 500 MB;
- format: MP4 or MOV;
- aspect ratio: 16:9, square pixel only;
- codec: H.264 or H.265;
- profile: Main or Baseline;
- frame rates: 23.976, 23.98, 24, 25, 29.97, 29.98, or 30 fps;
- video bitrate: minimum 1 Mbps; 4 Mbps or higher recommended;
- scan: progressive;
- audio: PCM, AAC, or MP3; mono/stereo;
- audio bitrate: minimum 96 kbps;
- audio sample rate: minimum 44.1 kHz.

Source: Amazon Ads, Sponsored Brands video ad specs.

## 8. Display / responsive eCommerce advertising

Amazon Ads supports responsive sizing and specific ad sizes. Examples in current official eCommerce creative specifications include placements such as:

- 300 x 250
- 336 x 280
- 160 x 600
- 300 x 600
- 728 x 90
- 300 x 50
- 320 x 50
- 414 x 125
- 980 x 55
- 970 x 250

Custom image dimensions and file-weight limits are placement-specific. Always map the actual ad slot before export.

Examples from current official spec:

| Ad slot | Custom image | Max file weight |
|---|---:|---:|
| 300x250 / 336x280 | 900x480 | 100 KB |
| 160x600 / 300x600 | 600x1020 | 100 KB |
| 728x90 | 1140x180 | 60 KB |
| 300x50 / 320x50 / 414x125 | 570x375 | 60 KB |
| 970x250 | 952x500 | 150 KB |

Source: Amazon Ads, eCommerce display creatives guidelines.

## Official source index

- Amazon Seller Central — Product image requirements: `https://sellercentral.amazon.com/help/hub/reference/external/G200498950`
- Amazon Seller Central — A+ Content comparison: `https://sellercentral.amazon.com/help/hub/reference/external/G202102930`
- Amazon Seller Central — A+ Content technical requirements: `https://sellercentral.amazon.com/help/hub/reference/external/GLG4RQK2Y2RJADU4`
- Amazon Ads — Stores creative guidelines: `https://advertising.amazon.com/resources/ad-specs/stores/`
- Amazon Ads — Sponsored Brands Video: `https://advertising.amazon.com/resources/ad-specs/sponsored-brands-video`
- Amazon Ads — eCommerce display creatives: `https://advertising.amazon.com/resources/ad-specs/ecommerce/`
- Amazon Sell — 3D/AR: `https://sell.amazon.com/tools/3d-ar`
