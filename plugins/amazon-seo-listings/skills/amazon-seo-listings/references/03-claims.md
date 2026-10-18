# Claims engine, claims firewall, forbidden keywords

> Source: original agent specification, sections preserved verbatim. Where this file conflicts with `SKILL.md` section "Precedence and errata", `SKILL.md` wins.

## 13. Claims Engine

Classify claims as:

- `VERIFIED_CLAIM`
- `SUPPORTED_MARKETING_CLAIM`
- `UNSUPPORTED_CLAIM`
- `REGULATED_CLAIM`
- `PROHIBITED_CLAIM`
- `AMBIGUOUS_CLAIM`

Examples requiring strict verification:

- waterproof
- water resistant
- clinical
- clinically tested
- clinically proven
- medical
- therapeutic
- antibacterial
- antimicrobial
- organic
- natural
- vegan
- cruelty-free
- hypoallergenic
- BPA-free
- non-toxic
- safe for children
- FDA approved
- dermatologist tested
- professional grade
- pregnancy safe
- certified
- eco-friendly
- sustainable

Never use a claim without sufficient evidence.

## 14. Claims Firewall

Use extra caution in:

- Beauty
- Cosmetics
- Supplements
- Food
- Medical
- Medical devices
- Children's products
- Toys
- Pesticides
- Electronics
- Automotive
- Batteries
- Health products
- Pet products

Claims must come only from:

- Verified TTX
- Verified packaging/label
- Verified catalog
- Verified manufacturer source
- Other explicitly approved source

SEO keywords are never evidence.

## 15. Claims Conflict Report

Before content generation, report risky SKUs.

Recommended fields:

- SKU
- Identifier
- Claim
- Source
- Risk
- Action

Example:

`UNSUPPORTED_CLAIM — "Clinically Proven" — no evidence found — exclude from listing`

## 16. Forbidden Keyword Layer

Maintain category- and marketplace-aware filtering.

Possible problematic terms include:

- best
- #1
- guaranteed
- cure
- cures
- FDA approved
- medically proven
- cheapest
- lowest price
- miracle
- competitor brands
- unsupported medical terms
- unsupported safety claims
- prohibited promotional language

Possible status:

`FORBIDDEN_TERM_FOUND`

Report:

- SKU
- Keyword
- Source
- Field
- Reason
- Action
