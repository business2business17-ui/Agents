# Category, attributes, origin, units, compatibility, duplicates, ASIN reconciliation

> Source: original agent specification, sections preserved verbatim. Where this file conflicts with `SKILL.md` section "Precedence and errata", `SKILL.md` wins.

## 17. Stage 3 — Category Resolution

Resolve:

- Amazon category
- Product Type
- Browse Node context when available

Return confidence.

Example:

- `product_type = HEADPHONES`
- `category_confidence = 0.97`

Possible statuses:

- `CATEGORY_CONFIRMED`
- `CATEGORY_HIGH_CONFIDENCE`
- `CATEGORY_REVIEW_REQUIRED`
- `CATEGORY_CONFLICT`

Do not force uncertain category assignments.

## 18. Category-Specific Overrides

Universal rules must not override Product Type / category-specific Amazon requirements.

If Product Type Definition or category schema requires:

- different attributes
- different title restrictions
- different variation rules
- additional compliance
- marketplace-specific enumerations

the category-specific Amazon rule wins.

## 19. Required Attribute Resolver

Determine which fields are:

- Required
- Conditionally required
- Recommended
- Optional

Examples:

- Voltage
- Wattage
- Dimensions
- Weight
- Capacity
- Material
- Color
- Number of Items
- Pack Quantity
- Battery Type
- Connectivity
- Age Range
- Skin Type
- Scent
- Flavor
- Compatibility
- Plug Type
- Included Components
- Safety Warnings

If a required field is missing:

`REQUIRED_ATTRIBUTE_MISSING`

Do not guess.

## 20. Country of Origin

Use only verified information.

Never infer country of origin from:

- EAN prefix
- UPC
- Brand headquarters
- Seller country
- Distributor country
- Warehouse location
- Marketplace
- Packaging language

Possible statuses:

- `COUNTRY_OF_ORIGIN_VERIFIED`
- `COUNTRY_OF_ORIGIN_CONFLICT`
- `DATA_REQUIRED`

## 21. Unit Normalization

Normalize units while preserving the source value.

Supported examples:

- mm / cm / m
- in / ft
- g / kg
- oz / lb
- ml / l
- fl oz
- V
- W
- Hz
- °C / °F

Store:

- Source unit
- Normalized value
- Marketplace display unit

Use local display conventions.

Never round engineering specifications in a way that changes product meaning.

## 22. Compatibility Engine

Store compatibility separately from general content.

Possible fields:

- `compatible_brand`
- `compatible_model`
- `compatible_generation`
- `compatible_year`
- `compatible_device`
- `compatible_platform`
- `not_compatible_with`

Never use broad compatibility language if only specific models are verified.

Possible statuses:

- `COMPATIBILITY_VERIFIED`
- `COMPATIBILITY_PARTIAL`
- `COMPATIBILITY_CONFLICT`
- `COMPATIBILITY_DATA_REQUIRED`

## 23. Duplicate Product Detection

Detect:

- Exact duplicates
- Near duplicates
- Same GTIN under different SKUs
- Same product under localized names
- Pack vs single confusion
- Duplicate child variations
- Same product with conflicting size/color/model

Possible statuses:

- `EXACT_DUPLICATE`
- `POSSIBLE_DUPLICATE`
- `PACK_SIZE_CONFLICT`
- `MODEL_CONFLICT`

## 24. Existing ASIN Reconciliation

If an existing Amazon ASIN is known/found, determine:

- `CREATE_NEW`
- `MATCH_EXISTING_ASIN`
- `UPDATE_EXISTING_ASIN`

Compare:

- Brand
- Model
- GTIN
- Size
- Count
- Manufacturer
- Color
- Variation
- Package quantity

Do not create a new product identity if evidence indicates it belongs to an existing ASIN unless explicitly instructed.
