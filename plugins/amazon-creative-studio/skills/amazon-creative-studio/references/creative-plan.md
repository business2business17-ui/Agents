# Checkpoint C1 - Plan Approval Template

One message, complete, so the user can answer `ok` or list exceptions by number. Never split the plan across several approval requests unless the mode is `GUIDED`.

## Message structure

**1. Understood (read-only summary)**
`Mode: SMART` - marketplaces/languages - number of SKUs - placements.

**2. Assumptions** (numbered; each with the default used)
`A1. Marketplace DE, copy language DE (not stated; derived from workbook column "Market").`
`A2. Row 14 classified Haircare / Shampoo - HIGH_CONFIDENCE_INFERRED.`

**3. Blockers** (only real ones, each with a recommended answer)
`B1. Row 7: rear view needed for slide 4 (usage). Options: (a) send rear photo, (b) use front 3/4 view <- recommended.`

**4. Plan per SKU** (table; one block per product row)

| # | Placement | Purpose (1 sentence) | Source asset | Headline / key copy (final language) | Layout (verbal wireframe) | Treatment (composite / generate-around / native text) | Status labels | Claim risk |
|---|---|---|---|---|---|---|---|---|

**5. What stays unchanged / what is edited or generated / what needs the user**

**6. Spec labels in play** - which dimensions are `AMAZON_REQUIRED`, `PRODUCTION_PRESET`, `VERIFY_IN_UI`.

**7. Ask** - `Reply "ok" to approve everything, or "3: ..., 8: ..." for exceptions. B1 default will be used if not answered.`

## After approval

Store approved items in project memory as `APPROVED` with date; anything the user delegated as `DELEGATED`. Proceed to production without asking again.
