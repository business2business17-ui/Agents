# Competitor reference: images and descriptions for a similar product

Purpose: study a competitor's listing (images, title, bullets, description, price/BSR/reviews) to position our own, similar product. The result is **reference only**: structure, feature coverage, gaps, price band. Nothing is copied.

## Source of the data (no scraping)

1. `scripts/amazon_link.py parse URL` -> marketplace + ASIN (any country); `plan URL` -> calls.
2. Helium 10 MCP (same marketplace as the link; ask the user to confirm it once):
   - `retrieve_listing_by_asin(asin, marketplace)` -> live `images` [{url, variant}], `product_name`, `item_highlight`, `bullet_points`, `description` (marketplaces US CA MX DE ES IT FR UK IN NL AU JP BE BR);
   - `get_listing_details(main_asin, marketplace)` -> price, BSR, reviews/rating, LQS, sales and revenue estimates, variations, top-10 keywords (US CA MX DE ES IT FR UK IN NL AE BR AU);
   - optional: `get_keywords_by_asin` (Cerebro), `search_competitors_by_asin`, price/BSR/review history tools.
   Save each result as JSON in `amazon-project/agent1/competitors/`.
3. `scripts/competitor_pack.py ingest LISTING.json [DETAILS.json] --marketplace XX --asin A --out DIR --download-images` -> `competitor_<ASIN>_<MP>.json` (the reference card) and `images/` (only the image URLs the tool returned, Amazon image hosts only, capped, sequential).
4. Not available (marketplace not in the tool list, MCP not connected): ask the user for screenshots / saved images / pasted text, or `amazon_link.py open URL` so the user looks and reports. Never scrape the page.

## What to do with the card

- **Look at the images** (open the downloaded files with your image viewer): count and order of images, MAIN image style, infographic / lifestyle / size / comparison / A+ patterns, what is shown in each slot, text density, claims on images. Describe, do not reproduce.
- **Read the copy**: how many bullets, what each bullet sells, order of benefits, spec coverage, tone, what is missing (gaps = our opportunity), objections answered.
- **Feature matrix**: `competitor_pack.py matrix CARD...` -> price, BSR, reviews, image and bullet counts, measurable features and certifications mentioned. Compare with OUR verified TTX; keep only what OUR product really has.
- **Competitor terms**: `competitor_pack.py brands CARD...` -> brand guess (confirm with the user) -> pass as `--competitors` to `seo_import.py` and `content_check.py`, so the brand never lands in our SEO or copy.
- Hand the analysis to the Design agent as a creative reference (layouts and slot ideas, not images to reuse).

## Hard rules

1. **Reference only.** Never reuse competitor text, images, brand, model names, claims or certifications. Our content is written from OUR verified TTX; competitor data is the lowest source in the hierarchy and is never evidence for our product.
2. **Copy guard before delivery.** `competitor_pack.py similarity CARD OUR_CONTENT.json` must PASS (no shared 6-word sequences above the limit). A FAIL blocks the record until the passage is rewritten from our own facts.
3. **Claims and certifications** seen on the competitor (waterproof, MIL-STD, IP rating, "organic", ...) are NOT carried over: each needs evidence for our product in the Evidence Matrix.
4. **IP review.** A similar product must not copy the competitor's design, trade dress, trademarks or patented features. Flag `IP_REVIEW_REQUIRED` in the handoff warnings and tell the user that a legal check of design / trademark / patents is theirs to do; this tool cannot judge infringement.
5. Record sources (tool, marketplace, ASIN, date) in project memory; competitor files stay in `agent1/competitors/` and are never sent to Amazon.
