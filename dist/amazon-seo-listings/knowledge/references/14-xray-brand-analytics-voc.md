# Market and performance reports: Xray, Brand Analytics, Voice of the Customer

Tool: `scripts/analytics_import.py FILE... [--marketplace XX] [--out analytics.json] [--emit-seo-csv F] [--emit-competitors F]`. It identifies each file by its headers (not by name), reads the metadata, applies the number format of the marketplace (DE/FR/IT/ES... use `16,99` and `13 666`) and returns facts plus relative signals. It never invents a marketplace: Brand Analytics and CX files carry none, so the agent asks (or reads `GB_`, `DE_`... from the file name).

| Report (how the user gets it) | Kind | What it gives | What the agent does with it |
|---|---|---|---|
| Helium 10 Xray of a category (top-100 products, XLSX) | `XRAY` | price spread (quartiles), monthly units and revenue (Helium 10 estimates), brand concentration, review barrier, rating, images, title length vs the 75-char rule, FBA share, new entrants, candidate competitor ASINs | Market entry view: price band for the pricing step (`margin_calc.py` for margins at that band), review barrier to plan, what the leaders show; competitor list is `REFERENCE_ONLY` and feeds `competitor_pack.py` via MCP calls, never copied |
| Brand Analytics - Search Catalog Performance (CSV, per ASIN) | `BA_CATALOG` | impressions -> clicks -> basket adds -> purchases, CTR, conversion, price median per ASIN | Diagnosis per ASIN vs the median of the file: `LOW_VISIBILITY` (indexing/keywords), `LOW_CTR` (main image, title start, price), `LOW_CONVERSION` / `CLICKS_NO_PURCHASE` (price, content, reviews, delivery), `LOW_SAMPLE` (fewer than 5 clicks: no conclusions). Turns into content/image tasks (Design agent) |
| Brand Analytics - Search Query Performance, brand view (CSV, per query) | `BA_SQP_BRAND` | query volume, brand impression / click / purchase share | Opportunity queries (high volume, low brand share), clicks without purchase; `--emit-seo-csv` makes a keyword file that `seo_import.py` accepts (SQP is verified demand for the brand, NOT the full market: add Cerebro/Magnet for breadth) |
| Brand share by quarter (CSV: total vs brand impressions, clicks, purchases) | `BA_BRAND_SHARE` | share and its change in percentage points between quarters | Trend statement only; missing quarters are named, never interpolated |
| Voice of the Customer / CX Health (CSV, per ASIN/SKU) | `VOC_CX` | negative-experience rate, star rating, return rate, health | Flags non-Excellent health and any NCX with its top reason; `LOW_SAMPLE` below 10 orders (an "Excellent" with 1 order means only "no complaints yet") |

Example files: the reports the user has shared so far are **samples from different accounts and businesses, a methodology for the format, not data about the current project**. Never copy their numbers into a project's memory or into another project's analysis.

An Xray export is taken from a **leaf (final) category**: the products in it are the market the new product enters. The file itself often does not name that category (blank `Category` column): ask for the full category path once, store it in `PROJECT.md` and use the same leaf for the browse node / Product Type choice (`amazon-categories.md`). A mixed export (several leaf categories) is a `CATEGORY_SCOPE_MIXED` finding: split it before computing benchmarks.

Every statement made from these reports carries its source label (printed by the tool): `Helium 10 Xray - ESTIMATES` vs `Amazon Brand Analytics - Amazon data`.

Rules
1. Ask what you cannot read from the file: marketplace and date of each report (one question, all files), the category of an Xray export whose Category column is blank, the brand the Brand Analytics files belong to.
2. Compare only same-period files (`PERIOD_MISMATCH`) and same-marketplace files (`MARKETPLACE_MISMATCH`). A 2025 query report and a 2026 catalog report describe different times.
3. Xray revenue and unit numbers are estimates; Brand Analytics numbers are Amazon's, for the brand and period given. Label which is which in every statement.
4. Thresholds (half of the file median, minimum clicks) are the tool's configuration, not Amazon rules. Small numbers are noisy: say so instead of drawing conclusions.
5. Nothing here is product evidence. Competitor titles, bullets, images and claims are never copied; claims need the seller's own evidence.
6. Reports of several accounts or projects are not mixed: each belongs to the project whose `PROJECT.md` names the brand.
