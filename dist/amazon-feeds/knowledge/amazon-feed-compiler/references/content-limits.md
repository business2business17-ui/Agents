# Listing content limits and country/language rules

Status: `USER_SUPPLIED` on 2026-10-11 (limits and language table given by the user). Corroborated by the US and UK feed templates (Data Definitions): the `title_differentiation` attribute, label "Item Highlight", says it "will appear only when the item name is under 75 characters" and "do not repeat information already in the item name". Everything else is not independently verified on Amazon pages. **The Product Type rule in the feed template / Seller Central for the chosen marketplace always wins.** Machine-readable copy: `content_limits.json`; checker: `scripts/content_check.py --marketplace XX`.

| Field (feed attribute) | Limit | Rules |
|---|---|---|
| Title (`item_name`) | **75 characters** incl. spaces (media category: 200) | ALL CAPS only for the brand; no promo phrases ("Free Shipping", "Best Seller"); a word at most 2x (prepositions/conjunctions exempt); over-limit titles may be shortened or rewritten by Amazon's AI |
| Item Highlights (`title_differentiation`) | **125 characters** | Feature / benefit phrases separated by commas, not sentences; indexed like the title; a word at most 2x; **no word that is already in the title** (no extra weight, wastes space); shown only when the title is under 75 characters |
| Bullet points (`bullet_point` x5) | each **10-255 characters** (some categories allow up to 500) | About 1000 bytes in total across the five are indexed; no emoji, check marks, asterisks; no punctuation at the end; the first 60-80 characters decide on mobile (before "Read more"); unique information per bullet |
| Description (`product_description`) | **2000 characters** | Plain text; HTML not supported (line-break tag is the only tolerated exception); with Brand Registry A+ Content takes priority; no ALL CAPS |
| Backend search terms (`generic_keyword`) | **bytes, not characters:** 249 (US, UK, EU), 500 (JP), 200 (IN) | UTF-8: ASCII = 1 byte, Cyrillic/Arabic/CJK/accented letters 2-4; one byte over = the whole field is ignored; separate by spaces, no commas; no repeats, no ASINs, no competitor brands |

Limits for marketplaces not listed in `content_limits.json` (`confirmed_for`) use the default and are flagged `BACKEND_LIMIT_UNCONFIRMED`.

## Seen in real feeds (user-supplied files, 2026-10-11)
- US feed `215_CELLULAR_PHONE_CASE` (1639 rows, `contentLanguageTag=en_US`): longest title 75, longest Item Highlight 124, longest bullet 155, 5 bullets per row, backend terms short (max 47 bytes). It is the reference style: Item Highlight holds features separated by `;`, none of the title is repeated in it.
- Older rows keep violating the new limits: US `223_PartialUpdate` has 255 of 413 titles over 75; the UK category feed has 33 of 33 titles over 75, no Item Highlights, some titles repeating a word more than twice; the DE copy-paste workbook has titles of 138-165 characters and backend terms of 281-335 bytes. `content_check.py` flags all of these.
- Feed columns: `item_name`, `title_differentiation` (Item Highlight), `bullet_point` x5, `product_description`, `generic_keyword`. Record actions seen: `Edit (Partial Update)` and `Create or Replace (Full Update)`.

## Countries and languages (`marketplaces.json`, `scripts/marketplaces.py`)

The seller must provide content in the **primary** language of the target country. Secondary languages are shopper-side (interface / automatic translation); own listings in them are `VERIFY_IN_UI`.

| Region | Marketplace: primary (secondary) |
|---|---|
| Americas | US: en (es) - CA: en and fr - MX: es - BR: pt |
| Europe | UK: en - DE: de (en, nl, pl, tr) - FR: fr (en) - IT: it (en) - ES: es (en, ca) - NL: nl (en) - BE: fr and nl - SE: sv (en) - PL: pl (en) - IE: en |
| Asia-Pacific | JP: ja (en, zh) - AU: en - IN: en (hi, ta, te) - SG: en (zh) |
| MENA / Africa | AE: ar and en - SA: ar and en - EG: ar (en) - TR: tr - ZA: en |

Countries with two primary languages (CA, BE, AE, SA) need one question per listing: "which language?". One record = one marketplace + one language; words of another language are never mixed in (SEO keywords, backend terms, copy).

## Verification routine
1. Read the real template: `xlsm_inspect.py FEED`; for the chosen Product Type compare Data Definitions (text hints, `Accepted Values`) with this file; a stricter template rule wins.
2. Search current rules online (`live-research.md`) when this file is older than 90 days or a rule looks changed; record a dated Research Note.
