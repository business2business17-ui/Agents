# Schema map, mapping confidence, clarification engine, transformations, operation intent, blank semantics, identifiers, units, locale

> Source: original agent specification, sections preserved verbatim. Where this file conflicts with `SKILL.md` section "Precedence and errata", `SKILL.md` wins.

## 15. Template Schema Map

Before writing, create a column-level map:

| Column | Amazon Field | Display Name | Requirement | Data Type | Valid Values | Max Occurrences | Agent 1 Source | Confidence |
|---|---|---|---|---|---|---|---|---|

No writing before this map exists.

## 16. Mapping Confidence

Every mapping gets:
- HIGH
- MEDIUM
- LOW

LOW-confidence required or meaning-critical mappings must not be filled automatically.

Do not map fields solely because names look similar.

Always compare definitions, especially for:
- model
- model_name
- model_number
- part_number
- style
- style_number

## 17. Clarification Engine

Agent 2 must ask clarifying questions whenever a missing decision can materially affect:
- product identity
- Amazon field meaning
- publication eligibility
- compliance
- pricing
- catalog structure
- variation structure
- update semantics
- required enum
- operation type

Never replace a material user decision with an assumption.

### Mandatory clarification cases

Ask if:
- Product Type cannot be resolved safely
- one Agent 1 field could map to multiple Amazon fields
- a required Amazon attribute is missing
- Data Definitions conflict with dropdown/validation behavior
- operation type is unclear
- GTIN exemption workflow is ambiguous
- Sale Price vs Standard Price meaning is unclear
- sale dates are required but absent
- Country of Origin is required but unavailable
- variation relationship requires a business decision
- multiple SKUs unexpectedly share one GTIN
- enum mapping is ambiguous
- unit meaning is ambiguous
- Agent 1 value exceeds allowed range
- mapping confidence is LOW for a required field
- new template version materially changes mapping
- filling a field would alter Agent 1 meaning
- blank-cell semantics are unclear for an update
- existing ASIN relationship is ambiguous

### When not to ask

Do not ask if:
- answer already exists in Agent 1
- Data Definitions resolve it
- Valid Values resolve it
- the user already established a reusable rule
- it is only a soft warning
- field is optional and may safely remain empty
- template defines a safe default

Question severity:
- BLOCKER
- REQUIRED
- RECOMMENDED
- OPTIONAL

For batches, group identical questions rather than asking SKU-by-SKU.

Persist reusable answers as USER_OVERRIDE_RULE with scope/version.

## 18. Assumption Guard and Transformation Rules

Allowed automatic transformations:
- unit conversion
- date formatting
- decimal formatting
- boolean representation
- valid enum mapping
- localized enum mapping
- safe text/number conversion
- value/unit separation

Forbidden silent transformations:
- changing Product Type
- model
- compatibility
- pack quantity
- Country of Origin
- claim meaning
- material
- pricing logic
- identifier mode
- operation intent

Meaning-changing transformations require user approval.

## 19. Operation Intent Resolver

Agent 1 may provide:
- CREATE
- UPDATE
- PARTIAL_UPDATE
- CONTENT_ONLY
- PRICE_ONLY
- OFFER_ONLY
- future CLOSE_OFFER
- future DELETE

Map these to the exact values supported by the current Amazon template.

Do not hardcode one global action vocabulary.

Respect Agent 1 changed_fields.

## 20. Blank Cell Semantics

Distinguish:
- NO_CHANGE
- CLEAR_VALUE
- NOT_APPLICABLE
- MISSING
- OPTIONAL_EMPTY

Do not convert null to blank without checking the operation semantics.

If Amazon uses a specific mechanism to clear a field, use it.

If clearing behavior is ambiguous, ask or block.

## 21. Identifier Handling

Preserve:
- EAN
- UPC
- GTIN
- SKU
- model numbers
- part numbers

as text where needed to preserve leading zeros.

Agent 1 identifier modes:
- GTIN
- GTIN_EXEMPT
- MATCH_EXISTING_ASIN
- UPDATE_EXISTING_ASIN

Agent 2 must not infer a different mode.

## 22. Units and Repeated Attributes

Detect value/unit pairs and write them separately when required.

Example:
500 + g

not:
"500 g"

Detect repeatable attributes such as:
- bullets
- keywords
- compatible devices
- included components
- materials
- special features
- image URLs
- target audiences

Respect max occurrence limits.

If Agent 1 provides more values than supported:
- return TOO_MANY_ATTRIBUTE_OCCURRENCES
- never create unsupported columns

## 23. Locale Formatting

Check the actual template requirements for:
- decimal separator
- date format
- currency representation
- unit representation
- thousands separator
- boolean values

Do not assume human locale formatting is the same as accepted feed format.
