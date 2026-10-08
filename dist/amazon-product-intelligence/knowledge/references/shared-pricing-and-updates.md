# SHARED POLICY - Amazon Pricing & Operation Requirements (v3, 2026-10-08-v3)

> Binding for Product Intelligence, Feed Compiler and Feed Error agents. Single source: `shared/amazon/` in the repository; each skill carries an identical copy (kept in sync by `tools/sync_shared.py`).
> Executable form of the price rules: `scripts/pricing_engine.py` (exact Decimal, self-test: `python3 scripts/pricing_engine.py --self-test`). Use the script; do not recompute prices by hand.
>
> **Errata (resolves contradictions found in the original specs):**
> 1. Missing B2B rate/basis is NOT a blocker. Rate 0.10 and basis STANDARD_PRICE are approved (see "B2B approved calculation test" below). Older text in the Agent 1 / Agent 2 / Error Agent specs that says "if B2B rate/basis are missing mark the record blocked" is superseded.
> 2. Write start row: the configured workflow is "Template rows 1-6 read-only, first data row 7". Agent 2's generic "never assume row 7" means: detect and verify; if detection disagrees with row 7, STOP with `TEMPLATE_ROW7_CONFLICT`; never silently shift the start row.
> 3. Business Price is applicable only where the current template has a supported B2B field; otherwise `business_price_status = NOT_APPLICABLE`.


## Approved user configuration (binding for all three agents)
- PRICE_INPUT_DEFAULT = sale_price. A single user-supplied price is a Sale Price, not Your Price.
- STANDARD_PRICE_POLICY = REVERSE_DISCOUNT; STANDARD_DISCOUNT_RATE = Decimal('0.10').
- BUSINESS_PRICE_POLICY = ALWAYS_CALCULATE_WHEN_APPLICABLE; BUSINESS_DISCOUNT_RATE = Decimal('0.10'); BUSINESS_PRICE_BASIS = STANDARD_PRICE; approved by user. Calculate for supported and applicable B2B offer fields.
- PRICE_UPDATE_SCOPE = ALL_RELATED_PRICES_BY_APPROVED_FORMULAS, limited to the requested price family and listing operation. Never recalculate MSRP/List Price or MAP without evidence, nor mutate unrelated catalog attributes.
- OPERATION_RESOLVER = AUTO_SELECT_WITH_PREVIEW. Never silently change CREATE into PARTIAL or vice versa when existing listing identity is uncertain.
- MISSING_REQUIRED_POLICY = BLOCK_AFFECTED_SKUS; return `NOT READY FOR AMAZON UPLOAD` for a combined feed containing blocked rows. Do not mark any blocked SKU ready.
- PRICE_POLICY_VERSION = `2026-10-08-v3`; all agents must reference this shared document, with no divergent local formulas.

## Deterministic price calculations
Input sale price `S > 0`; reverse discount `d = 0.10`:
`your_price / standard_price = quantize(S / (1-d), 0.01, ROUND_HALF_UP)`.
E.g. S=24.99 => standard_price=27.77; preserve S=24.99 unchanged. This arithmetic is a business rule, not proof that Amazon permits or will display a struck-through reference price.
Business Price `B = quantize(P * (1 - Decimal('0.10')), Decimal('0.01'), rounding=ROUND_HALF_UP)` where `P = quantize(S / Decimal('0.90'), Decimal('0.01'), ROUND_HALF_UP)` is Standard Price / Your Price. Calculate from the **rounded Standard Price**, never directly from Sale Price. Preserve user-supplied Sale Price `S` unchanged. Calculate only where B2B price is supported/applicable. If explicit price override conflicts with this policy, surface `PRICE_POLICY_CONFLICT` for user review; do not overwrite silently.
Validate 0<=d<1, 0<=b<1, prices >0, currency matches marketplace, optional guardrails min<=active_price<=max where applicable, quantities integer and tiers strictly ascending; dates valid and ordered; sale price < standard price under this policy. Round with exact decimal arithmetic only, using marketplace precision; never binary float.
Treat List Price/MSRP and MAP as evidence-driven independent fields: never fabricate these to manufacture a discount. Min/Max seller allowed prices and quantity tiers require their own approved guardrail/tier policy. If absent, do not invent or fill them. Sale dates need real user-defined dates when required by schema; otherwise block affected sale-price fields if required.
Calculate values in shared engine; populate **literal numeric values** in Amazon feed input fields unless current template explicitly expects formulas. Track input, policy, formula, unrounded, rounded, currency, timestamp, source, and version separately outside Amazon Template.

## Template-derived price mapping — CELLULAR_PHONE_CASE sample, Amazon US
Reference source: `CELLULAR_PHONE_CASE(1).xlsm`, `Template` rows 4 and 5, `Data Definitions` and `Valid Values`. These column letters are **specific to this template, not universal across all Amazon feeds**.
- DU: List Price (`list_price`)
- EX: Your Price USD (audience ALL) (`purchasable_offer ... our_price`), mapped from internal standard_price
- EZ/FA: minimum/maximum seller allowed price (ALL)
- FB: Sale Price USD (`discounted_price`)
- FC/FD: Sale Start / End Date
- FG: Amazon Business (B2B) Your Price (B2B audience)
- FH/FI: B2B min/max allowed price
- FL: quantity discount type (Fixed or Percent as supported by dropdown)
- FM/FN, FO/FP, FQ/FR, FS/FT, FU/FV: five quantity threshold/discount value pairs
- Confirm additional offer/pricing scheduling and automatic pricing fields by technical row-5 keys, rather than assumptions from display names.
- Template C: `Listing Action`. Use exact permitted values after resolving dropdown/Valid Values.

## CREATE vs FULL UPDATE vs PARTIAL UPDATE
For each new workbook inspect full `Template` row-5 machine keys, `Data Definitions`, `Valid Values`, dropdowns, instructions, all hidden attributes and correct marketplace/Product Type. Data Definitions `Required` is **not automatically the list for each Partial Update**.
Build a requirements matrix per field: `CREATE_REQUIRED`, `FULL_REQUIRED`, `PARTIAL_BASE_REQUIRED`, `PARTIAL_CHANGED_REQUIRED`, `CONDITIONAL`, `DEPENDENCY`, `NOT_NEEDED`, `UNKNOWN`, with evidence and exact row-5 key and column. Classify the operation before filling values.
- CREATE: full applicable required and conditionally required product/offer attributes, including identification and regulatory attributes.
- FULL UPDATE: comprehensive required set; warn that full replacement can remove omitted seller-contributed product facts. Do not use solely for price adjustments.
- PARTIAL UPDATE: existing SKU confirmed; include identification/action, changed attributes, required dependencies, and any operation-specific fields documented for that template; do not blindly fill every CREATE Required field. Where requirements are ambiguous, block and request evidence/approval.
- PRICE_ONLY / OFFER_ONLY are internal intents, not necessarily literal Listing Action values. Resolve them to `Edit (Partial Update)` or equivalent valid template action, and emit only permitted targeted price/offer fields + dependencies.
- `Delete` must never be selected without explicit approval.
- An external API (`patchListingsItem`) is **not identical to the Excel Listing Action**; do not assume all schema or omission semantics are portable. Verify for each submission mechanism.
- For the sample template, `Template` rows 1–6 are immutable, row 6 is illustrative, and all writes start row 7. Only Template is mutable; all other sheets must remain byte/semantic-equivalent, including validation/macros and hidden state.
- AUTO operation: if SKU/ASIN existence verified, prefer minimal partial update for price-only/field-only. If creation confirmed, CREATE/full as appropriate. If uncertain, set `OPERATION_REVIEW_REQUIRED` rather than guessing.
- Missing mandatory input => `MISSING_REQUIRED_ATTRIBUTE`, provide exact SKU, column, technical key, expected value/constraint, source, and why operation requires it; block affected SKU; never insert sample row-6 data or fabricated identifiers.

## Mandatory QA
Use shared, versioned pricing calculation + schema resolver in Agent 1, Agent 2 and Error Agent. Agent 2 exclusively writes Template starting row 7; other agents propose and validate. Build before/after preview for price mutations, no unexpected fields, cross-field checks and `PRICE_CALCULATION_AUDIT`. Block if B2B pricing validation fails, invalid prices, required partial fields, unresolved enumerations, missing sale date when required, unexpected write, changed protected areas, failed ZIP/workbook integrity, or stale policy.
Agent 1 hands off `price_input_type=sale_price`, `sale_price`, `standard_price`, `business_price_status`, `pricing_policy_version`, `pricing_basis`, `pricing_calculations`, `operation_intent`, `changed_fields` and `unresolved_required_fields`. Agent 2 maps exact template columns and validates. Error Agent performs minimal approved patches and uses the approved 10%-from-Standard-Price B2B policy and never silently changes formulas.

## Official context, not replacements for the user's workbook
- https://developer-docs.amazon.com/sp-api/lang-de_DE/docs/building-listings-management-workflows-guide
- https://developer-docs.amazon.com/sp-api/lang-en_EN/docs/manage-product-listings-guide
- https://developer-docs.amazon.com/sp-api/lang-en_US/changelog/reminder-december-2023-product-type-definition-changes-xsd-to-json-migration-requirements

## B2B approved calculation test / 2026-10-08-v3
- Example: Sale Price 24.99 -> Standard Price 27.77 (24.99 / 0.90, HALF_UP) -> Business Price 24.99 (27.77 x 0.90, HALF_UP).
- Verify business_price < standard_price; business_price may equal sale_price due to symmetric discounts for positive input, subject to target marketplace requirements; check active price/date interaction and Amazon validation results.
- `BUSINESS_PRICING_POLICY_REQUIRED` must NOT be emitted solely for missing B2B rate/basis: both are approved now.
- Store `business_discount_rate=0.10`, `business_price_basis=STANDARD_PRICE`, `pricing_policy_version=2026-10-08-v3` in handoff and audit records.


## Universal marketplace, language and attribute resolution — binding override / v3
- Support **every supported Amazon marketplace** and its relevant language, writing-system, currency and localized template. Never hardcode Amazon US, English, USD, category, product type, price letters, attribute names or listing action vocabulary. The `CELLULAR_PHONE_CASE` mapping is **illustrative only**.
- Re-discover every pricing field using the current workbook's machine headers, human-readable headings, `Data Definitions`, allowed values, validation formulas and contextual instructions; the number and semantic scope of pricing fields may change by marketplace, category, product type and template version. Do not transfer column letters from examples.
- Treat **Data Definitions** (or an equivalently localized semantic worksheet) as Amazon's primary instruction/reference for **how to fill attributes and which are Required/Conditionally Required**. Also inspect `Instructions`, `Valid Values`, dropdowns, examples, hidden columns and operation-specific notes; reconcile contradictions rather than assuming one status covers all operation types. Do not modify reference sheets.
- Recognize localized or renamed partial-update commands by their **field semantics and exact allowed values**, not by literal text `PartialUpdate` alone. Examples such as `Edit (Partial Update)` and `PartialUpdate` are distinct format-specific accepted values, not replacements that may be pasted interchangeably. Preserve exact local enum/capitalization from the actual template.
- Distinguish `CREATE`, `FULL_UPDATE`, `PARTIAL_UPDATE`, `PRICE_ONLY`, `OFFER_ONLY` as internal intents. `PRICE_ONLY` and `OFFER_ONLY` generally map to a template-allowed partial-update operation when identity and capability are verified; never assume they are literal template enums. Agent auto-selects the best valid action and displays the selection and affected SKU count to the user.
- **User-specified partial-update scope is authoritative:** when the user names fields/values to change, modify ONLY those attributes plus verified mandatory identity/action/dependent fields for that operation. Do not fill all attributes marked `Required` for create/full by default. Do not regenerate SEO, descriptions, catalog data, or unrelated prices. Do not interpret an unrequested blank as deletion. For changes to a Sale Price, the approved user's price-update policy permits recomputation of its related Standard and Business prices **when these prices are part of the requested pricing family and supported by the operation**, but no unrelated fields.
- Build an `OPERATION_REQUIREMENTS_MATRIX` for every current template, with field/technical key, localized label, column, marketplace, product type, operation, `Data Definitions` status, operation-specific required status, dependencies, supporting evidence, and confidence. Investigate exact **Partial Update** minimum input and extra required fields from instructions/accepted operation semantics and reliable Amazon docs; do not infer it merely from global `Required` labels. Any unresolved mandatory requirement blocks the affected SKU and generates a clear question/report.
- Preserve this project's hard write boundary: rows 1–6 read-only, example row 6 reference-only, write from row 7, `Template` only, other sheets untouched. If a future template contradicts this structure, STOP with `TEMPLATE_ROW7_CONFLICT` instead of silently shifting write position.
- Price computation: input `S` (Sale Price) exact; `P=ROUND_HALF_UP(S / 0.90, marketplace_currency_precision)`; `B=ROUND_HALF_UP(P * 0.90, marketplace_currency_precision)`; Business Price must use **P as already rounded**. Example EUR/USD 24.99 => P=27.77, B=24.99. Check supported B2B fields and local currency precision; do not invent List Price/MSRP/MAP or nonexistent columns.
- Treat pricing policy v3 as superseding all legacy B2B formulas and examples in historical sections. If any old statement or template-specific example conflicts, **v3 takes precedence**.
