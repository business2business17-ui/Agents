# SEO sources: Cerebro / Magnet exports and the Helium 10 MCP

SEO data is **search demand only**. It never proves a product fact, a claim, a compatibility or a feature (spec sections 3, 14). It is marketplace-specific: a US export is never translated into DE SEO (`SEO_MARKETPLACE_MISMATCH`).

## Country and language

- Any Amazon country. SEO is tied to **marketplace + content language**: `seo_import.py --marketplace XX --language yy` (language optional for single-language countries, mandatory for CA, BE, AE, SA, EG, IN). Keywords in another language are marked `WRONG_LANGUAGE` and excluded (loanwords such as English terms on DE can be kept with `--allow-languages en`); a file whose dominant language is not the target gets `SEO_MARKETPLACE_MISMATCH` / `SEO_LANGUAGE_MISMATCH`.
- Language detection: by script for ja / ar / hi, by distinctive words for en, de, fr, it, es, nl, pl, sv, pt, tr. Other languages are not detected: the agent checks them by reading, and states the language explicitly.
- A **Cerebro XLSX** export may start with title rows; the header row is found automatically. Thousand/decimal separators (12,400 / 12.400) are parsed.
- Cerebro/Magnet/MCP data for CA contains both English and French phrases: run once per language, with the matching `--language`.

## Choose the source (ask once, remember in `PROJECT.md` -> SEO sources)

| Source | When | How |
|---|---|---|
| **Export file** (Cerebro, Magnet, Black Box, ABA; CSV/XLSX) | the user already has files, or the marketplace is not available in the MCP | take the file as is; ask the export DATE and marketplace if the file does not state them |
| **Helium 10 MCP** (tools `mcp__Helium_10__*`) | the MCP is connected | pull with the tools below, save the result as CSV/JSON, then run `scripts/seo_import.py` |
| Both | best coverage | merge in `seo_import.py` (same marketplace only) |

Never pull or accept SEO for a marketplace other than the target record's marketplace.

## From an Amazon link to the right MCP call

The user may paste an Amazon product, category or search link of any country. Run `scripts/amazon_link.py parse URL` (offline) for marketplace, ASIN / browse node / keyword and the canonical URL, then `scripts/amazon_link.py plan URL` for the MCP calls with the right arguments and marketplace support (e.g. ASIN link -> `get_listing_details`, `retrieve_listing_by_asin`, `get_keywords_by_asin`; category node -> `search_products` with `filters.category=[node]`; search link -> `get_keywords_by_keyword`, `analyze_keywords`). The tool never scrapes pages; `open` only gives the URL to the user's own browser. The same ASIN can be missing or a different product in another country: verify per marketplace (`all-markets` lists the URLs).

## MCP tool map (use only the tools that are actually connected)

| Need | Tool | Key inputs |
|---|---|---|
| **Cerebro** - reverse search of an ASIN (own listing or a competitor) | `get_keywords_by_asin` | `asin`, `marketplace`; `exclude_variations` (default false = parent + children); optional `time_period` `YYYY-MM` |
| **Magnet** - expand a seed keyword (new product without ASIN) | `get_keywords_by_keyword` | `seed_keyword` (in the marketplace language), `marketplace` |
| Keyword database search (market-level discovery) | `search_amazon_keywords` | `filters` (word count, volume, competition...), `marketplace`, `limit` <= 200 |
| Score / enrich a candidate list | `analyze_keywords` | <= 200 phrases per call; **output order differs from input: match by `phrase`** |
| Merged, ranked keyword bank (<= 300 rows) | `find_keywords_with_multi_source` | `sources` (default `top_keywords` + `aba_converting_keywords`; ABA/SQP sources return nothing unless the seller's store is connected in Helium 10) |
| Top organic keywords of an ASIN group + competitor gaps | `get_top_keywords` | `main_asin`, optional `competitor_asins` (<= 10) |
| Keywords not yet tracked | `get_keywords_new_suggestion` | `asin_or_url` |
| Brand Analytics search terms, click/conversion share | `search_amazon_brand_analytics` | **needs Brand Registry** (otherwise permission denied) |
| After publication: is the ASIN indexed for keyword X? | `check_asin_keyword_index` | one ASIN, <= 50 keywords per call |
| Remaining quota | `get_mcp_usage_info` | call before a big pull |

## Rules for using the MCP

1. **Never invent an ASIN.** Cerebro needs a real ASIN: the user's own listing, or competitor ASINs the user names. A new product without ASINs starts from Magnet with seed phrases the user approves.
2. **Marketplace support differs per tool** (e.g. the Listing-Builder bank has BE but not AE/SA; Cerebro/Magnet/ABA support US CA MX DE ES IT FR UK IN NL AU JP AE BR SA). If the target marketplace (SE, PL, TR, IE, SG...) is not offered, report `SEO_SOURCE_UNAVAILABLE_FOR_MARKETPLACE` and ask for an export file; do not substitute another marketplace.
3. **Session handling.** The first call has no `session_id`; the result ends with `[gateway-meta] session_id=...`; pass exactly that value in every later call (also to sub-agents) and do not run calls in parallel before it exists. Give a one-sentence `context` on each call.
4. **Volume.** Prefer narrow queries over paging. `limit` up to 10,000 on Cerebro/Magnet; more than ~1,000 rows come back as a download (`data.export.download_url`); for big pulls use `response_format='download'` and `export_format='csv'`, fetch the file, run `seo_import.py` on it. Cursors expire after 30 minutes. One month per `time_period` request. Do not store signed download URLs in artifacts.
5. **Quota.** Every call consumes MCP quota: check `get_mcp_usage_info` before large batches and pull once per (marketplace, ASIN/seed), not once per SKU of a variation family.
6. **Provenance.** Record per source: tool or export name, marketplace, ASIN/seed, `time_period`, retrieval or export date, row count. This becomes `seo_source_date`, `seo_version` and the SEO sheet. A file's modification time is NOT the data date: ask.

## From data to content

1. Run `scripts/seo_import.py FILES --marketplace XX --product-terms "<from verified TTX>" --competitors "<brands>" --verified-claims "<claims with evidence>" --seo-date YYYY-MM-DD --out seo.json`. `--product-terms` come from the verified TTX / product type (never from the keyword list itself).
2. Show the **SEO Sanitization Report** (counts: total, usable, irrelevant, competitor, prohibited, unsupported claims, exact duplicates, semantic-duplicate clusters, tiers 1-4, excluded) and any flags (`SEO_MARKETPLACE_MISMATCH`, `SEO_SOURCE_OLD`). A mismatch stops SEO use for that marketplace until the user decides.
3. Use tiers as suggested placement: Tier 1 -> title, Tier 2 -> highlights/bullets, Tier 3 -> bullets/description, Tier 4 -> backend terms (semantic duplicates are good backend synonyms). Then write content and verify with `scripts/content_check.py`.
4. Put `seo.json` into the record (`record["seo"]`) so it appears in the SEO sheet of the review XLSX and in the versions (`seo_source_date`, `seo_version`).
5. `top1` / `top2` counts and the relevance thresholds are tunable configuration, not Amazon rules. The agent still reads the final keyword list: a keyword is used only if the product really has that attribute.
