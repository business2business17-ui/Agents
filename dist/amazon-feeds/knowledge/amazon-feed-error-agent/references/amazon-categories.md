# Amazon categories, product types, country - mandatory intake and knowledge base

Every project starts by fixing three facts per product group: **category**, **product type**, **country (marketplace) + listing language**. They decide claims, compliance, required attributes, feed template, image rules, SEO language and prices. Never guess them silently and never reuse them across a mixed matrix without confirming.

## 1. The intake question (ask once, one message, recommendation pre-filled)

Group the products by identical (category, product type) pair and ask:

```
Подтвердите по группам / Confirm per group:
G1 (rows 2-14, 13 pcs): category = <recommended>, product type = <recommended>
G2 (rows 15-20, 6 pcs): category = <recommended>, product type = <recommended>
Страна(ы) / marketplace(s): <recommended, from file/memory>   Язык листинга / listing language: <recommended>
ok - or reply: G2: Home & Kitchen / <type>; countries: DE, FR
```

Rules:
- Infer the recommendation from title, TTX, brand, GTIN prefix, template (`Product Type` cell, browse node), file name, project memory. If the user already answered in this project (PROJECT.md), do not ask again; only re-ask for new rows.
- A mixed matrix is normal: classify **each row**, then group. A row that does not fit any group is asked about separately by row number.
- Country: any Amazon marketplace (`marketplaces.py --list`). Language depends on the country; for multi-language marketplaces (CA, BE, AE, SA, EG, IN, and others in the table) ask which listing language(s). One record = marketplace + language. Currency, units, VAT, size charts, compliance and keyword language follow the country.
- Store the answers in PROJECT.md (`category`, `product_type`, `marketplace`, `language`, `date`) and use them everywhere: they are inputs, not assumptions to re-derive.
- If the category is gated/restricted for the seller (section 4), say so at the checkpoint; do not continue to "ready" status until the user confirms approval status.

## 2. Top-level categories (general knowledge, US-style names; names and availability differ per country)

Appliances - Arts, Crafts & Sewing - Automotive - Baby - Beauty & Personal Care - Books - Cell Phones & Accessories - Clothing, Shoes & Jewelry (Apparel, Shoes, Jewelry, Watches, Luggage) - Collectibles & Fine Art - Computers - Electronics - Grocery & Gourmet Food - Handmade - Health & Household - Home & Kitchen - Industrial & Scientific - Musical Instruments - Office Products - Patio, Lawn & Garden - Pet Supplies - Software / Video Games - Sports & Outdoors - Tools & Home Improvement - Toys & Games - Amazon Devices - Gift Cards.

**Product type** is the finer level: the feed's Product Type value (for example `SHAMPOO`, `HEADPHONES`, `SHOES`) and the browse node (category path). The exact list for a marketplace comes from the feed template's own dropdown / the product type definitions - use those, not memory. Browse nodes can be searched with the Helium 10 MCP `search_browse_nodes` (US UK FR IT DE ES JP) or the seller's category browser.

## 3. What the category changes (starting checklist, verify live - see live-research.md)

| Area | Typical effect |
|---|---|
| Images | Apparel/Shoes/Jewelry: model or on-figure shots may be required or expected, different MAIN rules; Books/Media: cover; Grocery/Beauty/Health: label legibility and net content visible; Home: scale and in-use context |
| Required attributes | Differ per product type (size, color, material, voltage, age range, ingredients, batteries, country of origin...) - read the template, never invent values |
| Claims | Health/medical, "natural/organic/eco", "anti-aging", "clinically proven", child-safety, "waterproof" ratings need documentary proof; translation must not strengthen a claim |
| Compliance docs | Electronics: CE/UKCA/FCC, WEEE, batteries; Toys: toy-safety standard marks (EN 71 / CPSIA); Cosmetics: EU Responsible Person + CPNP notification, INCI list; Food: ingredients, allergens, best-before; Chemicals: CLP/SDS; Textiles: fibre composition labeling; Packaging EPR registrations (for example Germany LUCID); General product safety information (EU GPSR: manufacturer and EU responsible person details) |
| Hazmat / shipping | Aerosols, batteries, flammables, liquids may need classification before FBA |
| Language / format | Units (cm/in, kg/lb), decimal separators, size systems (EU/UK/US), dates and VAT follow the country |

## 4. Gated / restricted (approval often required - verify for the seller account and country)

Commonly restricted or requiring approval: certain Beauty and Personal Care, Grocery and Gourmet, Health supplements and OTC, Baby products, Toys (seasonal), Jewelry and Watches, Fine Art, Collectibles, Automotive parts, some Electronics brands, Alcohol, Medical devices, Hazmat. Do not declare a product "ready" when the user has not confirmed approval; list it as `BLOCKED_BY_GATING` with the exact thing to confirm.

## 5. Freshness

Category trees, restrictions and compliance rules change. This file is a map, not the source of truth. Before production-critical decisions follow `live-research.md` (official Amazon pages for the chosen country, dated) and record what you found in PROJECT.md. If you cannot search, label every rule `VERIFY_IN_UI` / `VERIFY_IN_SELLER_CENTRAL`.
