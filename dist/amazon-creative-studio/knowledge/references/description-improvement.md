# Product Description Improvement

For every product (per row, per category and type) the agent audits the description it has and proposes a better one, based on the TTX, the confirmed category and the confirmed product type. It is a proposal: the user approves it at C1, nothing is written back into the source XLSX.

## Inputs per product

`existing_description` (from `match.json`: description / title / bullets columns, if any), `facts` (TTX), `benefits`, confirmed `category` + `product_type`, target marketplace and language.

## Audit (per product)

1. **Coverage vs. type.** What a shopper of this category/type expects to find (examples: cosmetics - volume, texture, application, skin/hair context, key supported ingredients; electronics - dimensions, power, runtime, ports, compatibility, what is in the box; apparel - sizes, material, care, fit; household - capacity, material, dimensions, maintenance, included parts). List expected attributes that the TTX does not contain as `MISSING_TTX` with the exact question to the user. Do not fill them.
2. **Weak spots.** Raw / copy-pasted / machine-translated text, repeated facts, vague adjectives ("best", "premium", "high quality") without proof, wall of text, facts buried below fluff, inconsistent units.
3. **Contradictions.** Description vs. TTX (number, unit, material, model, quantity). TTX wins only if the user confirms; otherwise flag it.
4. **Claim risk.** Medical, health, safety, eco, certification, ranking, award, comparative or guarantee claims without a supplied proof -> `REMOVE_OR_PROVE`.
5. **Visual fit.** Which facts are strongest as image copy (carousel 2-7, A+) and which belong only in native text.

## Proposal (per product, in the marketplace language)

| Field | Content |
|---|---|
| Current | the existing text, short quote, or `NONE` |
| Issues | numbered list from the audit |
| Proposed description | complete text built only from TTX + approved benefits; short paragraphs or bullets; facts first, units exact |
| Change log | each new sentence -> the source fact (`TTX: <header>`) |
| Missing information | `MISSING_TTX` questions, deduplicated across products of the same type |
| Claims removed / needs proof | with reason |

Rules: never invent a fact, a benefit, a certification or a use case; never strengthen a claim in translation; keep brand and model names exactly; the proposal is marketplace-language text, the audit is in the chat language. Length and formatting follow the placement (image copy is short; the description proposal is a text for the product page and is not limited by the image layout).

Scope: this is description-level content that feeds the visuals and the product page. Full title / bullets / backend-keyword SEO belongs to `amazon-product-intelligence` (Agent 1); hand over the approved description and the `MISSING_TTX` list instead of duplicating that work.

## Output

- `CONTENT_INTELLIGENCE` rows (`Draft Copy` = proposed description, `Missing Proof / Input`, `User Approval Status`).
- `ISSUES` rows for contradictions and removed claims.
- One compact block per product at C1; products of the same category/type with the same gaps are summarized together ("12 shampoos: volume and application are missing from the TTX").
